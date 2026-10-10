# QShield SecureAccess

Quantum-Resilient Cyber-Physical Security for Connected Access-Control Systems.

QShield SecureAccess is a research and prototype simulation that models how a connected access-control network can decide whether a device is legitimate, physically present, behaving normally, and trustworthy before allowing it into the security network. It is not a production access-control product.

The project preserves the existing QShield concepts and applies them to realistic building access-control devices such as door controllers, smart locks, RFID readers, mobile credential gateways, and security sensors.

## What It Does

- Simulates an access-control building network with realistic zones and device identities.
- Reuses the existing Ghost/Sybil attack engine to model duplicate or fake device identities.
- Uses the existing proof-of-proximity and software-simulated Time-of-Flight verification path.
- Uses the existing simulated lattice-based PQC interface for device authentication.
- Uses the existing multi-factor trust engine to produce accept, monitor, reject, or blacklist decisions.
- Records audit events in the existing 8-shard hash-based ledger.
- Streams live security events to the React dashboard over WebSocket.
- Exports analytics and validation results as JSON or CSV.

## Real-World Problem

Connected access-control systems need to answer a practical question before trusting a new device:

Can this door controller, reader, lock, or gateway be verified as an expected device in the right place, with a valid identity, and with behavior that matches the network policy?

This prototype models that cyber-physical security layer. It is intended to demonstrate how a system can detect suspicious identities, duplicate devices, and ghost-style attacks before granting access to the network.

## Architecture

```text
Connected Access Device
        ↓
Identity Authentication
        ↓
Proof-of-Proximity + ToF
        ↓
PQC Verification
        ↓
Sybil/Ghost Detection
        ↓
Multi-Factor Trust
        ↓
Security Decision
        ↓
8-Shard Audit Ledger
        ↓
Real-Time Security Dashboard
```

## Security Workflow

1. Device discovery detects a new access-control device attempting to join.
2. Identity check uses the simulated lattice-based PQC interface.
3. Physical verification uses the software-simulated proof-of-proximity and ToF path.
4. Sybil/Ghost detection identifies duplicate, clone, or suspicious identities.
5. Trust evaluation combines the available signals into a security score.
6. Security decision returns `ACCEPT`, `MONITOR`, `REJECT`, or `BLACKLIST`.
7. Audit records are written to the local 8-shard hash-based ledger.
8. Real-time events are streamed to the dashboard through WebSocket.

## Example Device Model

The SecureAccess scenario uses access-control terminology such as:

- Main Entrance Door Controller
- Server Room Door Controller
- Office Door Smart Lock
- RFID Access Reader
- Mobile Credential Gateway
- Security Floor Gateway
- Emergency Exit Controller
- Access-Control Sensor

The configured attack scenario can also introduce suspicious identities. These
carry **neutral names** (for example `access-node-0001`): they are distinguished
only by observable behaviour — a spoofed proof-of-proximity measurement, a shared
(cloned) credential, elevated traffic and repeated signature failures — not by any
name or label.

## Technical Honesty

- The PQC layer is a simulated lattice-based cryptography interface, not production Kyber or Dilithium.
- The proximity layer is software-simulated ToF verification, not hardware-grade ranging.
- The ledger is a local 8-shard hash-chained, tamper-evident audit ledger, not a blockchain or distributed consensus network. Use `GET /api/v1/security/ledger/integrity` to verify it.
- The demo metrics are simulation results from a configured scenario, not real-world deployment accuracy.
- Detection uses a transparent **feature-based** detector (`ghost-detector/2.0`, in `backend/security/detection/`) that reads only observable telemetry — never scenario labels, names or ids. It is evaluated on held-out scenario distributions, including a deliberately hard "stealth" suite where its recall is honestly **0%**. Reported precision/recall still characterise the simulator, not real-world performance. Run `uv run python -m backend.security.detection.run_evaluation` to reproduce.
- Missing, stale, malformed or contradictory telemetry is reported as an explicit **unknown** outcome, not a benign pass. A security-sensitive access-control join with unknown telemetry is escalated to `challenge` (not accepted), and unknown events are excluded from the confusion matrix so they are never counted as true negatives.
- API/WebSocket authentication is an **opt-in shared token** (`API_TOKEN`); when unset (local development) the API is open. Production requires the token (validated at startup). The token is held **server-side** only (the Vite dev proxy in development, a reverse proxy in production, via a non-`VITE_` variable) and is **never** shipped to the browser — a `VITE_`-prefixed value is public. This is a deployment-level gate, **not** user authentication (no RBAC). Rate limiting is in-process, not an edge-grade limiter.

## Repository Layout

- `backend/` FastAPI backend, digital twin, security pipeline, ledger, analytics, validation.
- `backend/security/detection/` feature-based ghost detector + independent evaluation harness (`run_evaluation`).
- `frontend/` React + TypeScript + Vite dashboard.
- `tests/` backend and security tests.
- `backend/validation/security_demo.py` scripted SecureAccess demonstration.

## Prerequisites (Arch Linux)

- Python **3.12+** and [`uv`](https://docs.astral.sh/uv/): `sudo pacman -S python uv`
  (or `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Node.js **20+** with npm (Bundled with `sudo pacman -S nodejs npm`).
- Optional: Docker with the Compose v2 plugin (`docker compose`).

## Run Backend

```bash
uv sync                                # install deps from uv.lock
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the helper script: `./scripts/start_backend.sh`.

## Run Frontend

```bash
cd frontend
npm ci            # reproducible install from package-lock.json
npm run dev       # dev server on http://localhost:5173
```

The dev server proxies `/api` (and the WebSocket) to the backend
(`VITE_API_PROXY_TARGET`, default `http://localhost:8000`), so no CORS setup is
needed. Copy `frontend/.env.example` to `frontend/.env.local` to override the
API/WebSocket URLs.

Other frontend commands:

```bash
npm run typecheck   # tsc --noEmit
npm run build       # production bundle in dist/
```

## Run the Security Demonstration

```bash
uv run python -m backend.validation.security_demo
```

The demo runs a configured access-control scenario with legitimate devices and simulated ghost identities, then prints the resulting metrics and writes a JSON report to `logs/secureaccess_demo_results.json`.

## Reproducible Experiments

Scenario runs accept an optional `seed`. When set, all stochastic components
(ghost behaviour, proximity noise) and the exported analytics metadata are
reproducible, so a result set can be re-run and audited:

```bash
curl -X POST http://localhost:8000/api/v1/simulation/scenario/medium_sybil_attack \
  -H 'Content-Type: application/json' \
  -d '{"device_count": 100, "ghost_count": 20, "seed": 42}'
```

Exported analytics include `metric_source: "simulation"`, the `seed`, the
scenario name, and the software version.

## API Endpoints

Core endpoints used by the dashboard and demo:

- `GET /api/v1/security/status`
- `GET /api/v1/security/access-control/overview`
- `GET /api/v1/security/access-control/devices`
- `GET /api/v1/security/access-control/devices/{device_id}`
- `GET /api/v1/security/access-control/events`
- `POST /api/v1/security/demo/access-control`
- `POST /api/v1/security/attack/start`
- `POST /api/v1/security/attack/stop`
- `GET /api/v1/security/ledger`
- `GET /api/v1/security/ledger/integrity`
- `GET /api/v1/security/trust`
- `GET /api/v1/security/analytics`
- `GET /api/v1/security/verification/metrics`
- `GET /api/v1/ws/stream`

Other existing simulation and network endpoints remain available for the digital twin.

## Testing

```bash
uv run pytest          # full test suite (isolated temp database)
uv run ruff check .    # lint
```

The test suite covers configuration validation, the access-control and security
pipeline, research-metric correctness (ground-truth vs. detector separation and
seed reproducibility), ledger integrity/tamper detection, and request
validation. Tests never touch the developer's real `qshield_twin.db`.

## Docker

```bash
cp .env.example .env    # set SECRET_KEY etc. if you plan to run in production mode
docker compose up --build
```

Backend on `:8000`, frontend on `:5173`. This requires the Compose **v2**
plugin (`docker compose`). The backend image runs as a non-root user and ships a
container healthcheck. See `docs/ARCHITECTURE.md` for production guidance.

## Documentation

- `docs/ARCHITECTURE.md` — components and data flow.
- `docs/ENGINEERING_AUDIT.md` — what was changed and why, with evidence.
- `SECURITY_FRAMEWORK_IMPLEMENTATION.md`, `SECURITY_QUICK_START.md` — security notes.

## Limitations

- This is a prototype and simulation environment.
- The cryptography, proximity, and ledger layers are intentionally modeled abstractions.
- Detection and trust scores are scenario-dependent and should not be interpreted as deployment-grade security guarantees.
- Real hardware integration would require device APIs, secure provisioning, and operational validation beyond this codebase.
