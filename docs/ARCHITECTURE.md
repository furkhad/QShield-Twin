# QShield Twin — Architecture

This document describes the components, data flow, and simulation boundaries of
the QShield Twin / SecureAccess prototype. Read it together with
`docs/ENGINEERING_AUDIT.md` (what was changed and why) and the honesty notes in
`README.md`.

## Overview

QShield Twin is a **research simulation** of a cyber-physical access-control
security pipeline. It answers, in simulation: *should this device be trusted to
join the network, based on identity, (modelled) physical proximity, behavioural
signals, and history?*

It is not a production access-control product and does not implement real
cryptography or real physical ranging.

## Components

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API | `backend/app/` | FastAPI app, routers (`/api/v1`), request/response schemas, WebSocket, middleware |
| Orchestration | `backend/digital_twin/manager.py` | Singleton `DigitalTwinManager`: owns the simulator + security pipeline, runs scripted scenarios |
| Simulation | `backend/simulation/` | SimPy-based device simulation, topology/network graph, packets |
| Security | `backend/security/` | Ghost/Sybil engine, proximity, PQC (simulated), trust, ledger, analytics |
| Persistence | `backend/database/`, `backend/models/`, `backend/repositories/` | SQLAlchemy models/repos (device registry) |
| Config | `backend/settings.py` | Validated, environment-driven settings |
| Frontend | `frontend/` | React + TypeScript + Vite dashboard and research UI |

### Security pipeline (`backend/security/orchestrator.py`)

On a device join (`receive_join`) or packet (`receive_packet`) the orchestrator
runs a fixed sequence:

1. **Identity / PQC** — `SimulatedLatticeCrypto` (synthetic keypair, sign, verify;
   timing/metrics modelling only).
2. **Observation extraction** — an observable-only `Observation` is built from
   telemetry (proof-of-proximity measurement, signature outcome, packet rate/size,
   credential fingerprint, trust). Scenario labels, names and ids are never read.
3. **Proof-of-Proximity** — `ProofOfProximityEngine` compares the observed
   measurement to the claimed position within a tolerance.
4. **Ghost/Sybil detection** — the feature-based `GhostDetector`
   (`backend/security/detection/`, version `ghost-detector/2.0`) scores the
   observation with a noisy-OR combination of proximity, signature-failure,
   traffic, identity-cluster, credential-reuse and trust evidence, and returns an
   explainable decision (`score`, `features`, `reasons`). If the telemetry is
   missing, stale, malformed or self-contradictory the outcome is an explicit
   **unknown** (`status` / `is_unknown`) rather than a benign pass; a
   security-sensitive access-control join is escalated to `challenge` and is not
   accepted. `GhostEngine` still tracks attack campaigns.
5. **Trust** — `TrustEngine` folds proximity, signature, and behavioural
   evidence into a score and an `accept` / `monitor` / `reject` / `blacklist`
   decision. An unknown detector outcome can only *tighten* a decision (allow →
   `challenge`), never loosen one.
6. **Ledger** — the decision, evidence and detector explanation are appended to
   the sharded, hash-chained audit ledger.
7. **Analytics** — ground-truth label and detector output are recorded
   **separately** for confusion-matrix computation, with detector version/score.
   Unknown outcomes are recorded with `observed=False` and excluded from the
   confusion matrix (so they are never counted as true negatives), and reported
   under `observation_coverage`.
8. **Events** — a summary is emitted (recorded + broadcast to WebSocket clients).

## Data flow

```text
Scenario / API request
      │
      ▼
DigitalTwinManager.run_scenario(seed=…)
      │  builds access-control devices (legitimate + ghost)
      ▼
Simulator ──packet_callback──▶ SecurityOrchestrator
      │                              │
      │                              ├─▶ engines (PQC, proximity, ghost, trust)
      │                              ├─▶ ShardedLedger (hash-chained)
      │                              └─▶ AnalyticsEngine (confusion matrix, run metadata)
      ▼
status() ──▶ /api/v1/security/* ──▶ React dashboard
      └────▶ emit_sync ──▶ WebSocket /api/v1/ws/stream
```

## Configuration & secrets

All backend configuration lives in `backend/settings.py` and is read from the
environment (and an optional `.env`). In `ENVIRONMENT=production` the app
**refuses to start** with placeholder secrets, `DEBUG=true`, wildcard CORS/hosts,
or SQLite. See `.env.example`.

The frontend reads `VITE_API_BASE_URL` / `VITE_WS_URL` /
`VITE_API_PROXY_TARGET` (see `frontend/.env.example`); in development the Vite
server proxies `/api` (including the WebSocket) to the backend, so REST calls
are same-origin and no CORS setup is required.

### API token is held server-side (never in the browser)

Vite statically inlines **every** `VITE_`-prefixed variable into the client
bundle, so a `VITE_`-prefixed value is public and must never hold a secret. The
optional shared backend token (`API_TOKEN`) is therefore **not** given to the
browser. Instead a server-side component injects the `X-API-Token` header when
forwarding `/api`:

- **Development:** the Vite dev-server proxy (`frontend/vite.config.ts`) reads the
  non-`VITE_` variable `QSHIELD_API_TOKEN` (environment or
  `frontend/.env.local`) and injects the header on REST requests and the
  WebSocket upgrade. Leave it unset and the backend is open (local development).
- **Production:** a reverse proxy injects the header in front of the static
  bundle. Minimal nginx sketch:

  ```nginx
  server {
    listen 443 ssl;
    root /srv/qshield/dist;

    location /api/ {
      proxy_pass http://backend:8000;
      proxy_set_header X-API-Token $QSHIELD_API_TOKEN;  # set via env/secret
      proxy_set_header Host $host;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;           # WebSocket
      proxy_set_header Connection "upgrade";
    }
    location / { try_files $uri /index.html; }
  }
  ```

This is a **deployment-level gate, not user authentication** — it blocks
anonymous public access but provides no per-user identity or RBAC. Never put the
token in a `VITE_`-prefixed variable. `npm run check:secrets` fails the build if
a token ever ends up in the bundle.

## Research reproducibility

Scenario runs accept an optional `seed`. When provided, the ghost engine and
proximity noise are seeded, and the analytics export carries
`metric_source: "simulation"` plus `run_metadata` (seed, scenario,
software version). Detection metrics are computed from a confusion matrix whose
`is_ghost` (ground truth) and `detected_as_ghost` (detector output) inputs are
kept separate.

## Simulation boundaries (what this is NOT)

- **Not real cryptography.** PQC operations are synthetic and provide no security.
- **Not real proximity.** Distance is modelled from a path delay + noise, not
  hardware ranging (e.g. UWB).
- **Not a blockchain / distributed ledger.** The ledger is a single-node,
  hash-chained, tamper-evident log with no replication or consensus.
- **Not validated.** Metrics characterise the simulator against synthetic
  ground truth; no field or adversarial validation has been performed.

## Deployment

### Development

- `backend/Dockerfile` — Python 3.12, dependencies installed reproducibly from
  `uv.lock`, runs as a non-root user, includes a healthcheck.
- `frontend/Dockerfile` — Node 22, `npm ci`, Vite dev server.
- `docker-compose.yml` — dev stack (`docker compose up --build`), requires the
  Compose v2 plugin. Source trees are bind-mounted for hot reload.

### Production

- `frontend/Dockerfile.prod` — multi-stage: `npm ci` + `vite build` in a Node
  stage, then the compiled `dist/` served by `nginx:1.27-alpine`. No Node and no
  application source ship at runtime.
- `backend/Dockerfile` — reused unchanged; still non-root, still installed from
  `uv.lock`.
- `docker-compose.prod.yml` — production stack: frontend (nginx) + backend +
  PostgreSQL, no bind mounts, backend/DB not published to the host. Only the
  frontend port is exposed, bound to `127.0.0.1` by default.
- `scripts/build-prod-images.sh` — builds images tagged
  `ghcr.io/furkhad/qshield-twin-{backend,frontend}:<tag>` locally, so the same
  Compose file works before and after GHCR publishing (nothing is pushed).
- `frontend/nginx/default.conf.template` — serves the SPA, proxies `/api`
  (REST + WebSocket) to the backend, and injects the `X-API-Token` header
  **server-side** so the token never reaches the browser.

The production deployment requires a networked database: `ENVIRONMENT=production`
rejects SQLite, and the backend image ships the `psycopg` 3 driver. The token
injected by the proxy is a deployment-level gate, **not** user authentication.
See `docs/DEPLOYMENT.md` for the full flow, secrets, persistence and the list of
things that are deliberately **not** claimed as production-ready.
