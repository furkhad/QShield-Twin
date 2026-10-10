# QShield Twin — Engineering Audit

**Date:** 2026-10-10
**Scope:** Full-stack principal-engineer review of the QShield Twin / SecureAccess
repository: correctness, security, research integrity, frontend, packaging,
deployment, and documentation.
**Baseline:** committed as `baseline before principal-engineer upgrade`
(158 tracked files). A recoverable archive was taken at
`/tmp/opencode/QShield-Twin-baseline-20261010-183255.tar.gz`.

This document records *what was wrong*, *what changed*, and *what is verified*.
Everything below is reproducible from the commands in §5.

---

## 1. Method

1. Inventory the tree, entry points, and tests; run the app and frontend from
   scratch in a clean environment.
2. Read every backend module in the request path (API → manager → simulator →
   security orchestrator → engines → ledger → analytics).
3. Read the frontend data layer (fetch/WebSocket usage, chart pages, research
   report generator) against the actual backend response shapes.
4. Fix high-value defects with small, targeted changes; add regression tests.
5. Run: `ruff`, `pytest`, coverage, `tsc --noEmit`, `vite build`, `uv lock/sync`.
6. Document honestly, including limitations that were **not** fixed.

No system Python was modified. No unrelated files were deleted.

**Revision (follow-up pass).** This document was updated after a second
hardening pass that: normalised line endings/whitespace (§3.6), upgraded the
frontend dependencies (React Router 7, Vite 6, `@vitejs/plugin-react` 4.7 —
§3.5), migrated the test client to Starlette's supported `httpx2` (§3.1),
fixed a `/data` volume ownership bug in `backend/Dockerfile`, and built and ran
both Docker images directly (§5).

The Docker CLI/daemon **is** available, but the **Compose v2 plugin is not**
(there is also no legacy `docker-compose`), so `docker compose` itself could not
be executed. The individual images *were* built and run with `docker build` /
`docker run`, covering backend health/endpoints/graceful-shutdown and
frontend→backend proxy integration (see §5, §6).

**Revision 2 (Phase 2 — detection intelligence & security hardening).** A third
pass replaced the name-token ghost detector with a feature-based detector and an
independent evaluation harness (§9.1–§9.2), added API/WebSocket authentication,
rate limiting, request-size limits and a WebSocket connection cap (§9.3), fixed
attack-campaign metric accounting and frontend data contracts (§9.4). A final
security-review pass then removed the browser-side API token in favour of a
server-side proxy that holds the secret (§9.5), made missing/degraded telemetry an
explicit `unknown` outcome instead of a silent pass (§9.6), and extended the test
suite and CI (§9.7–§9.8). The residual *name-token leakage*
listed in §2.3/§6.1 is now **resolved**; the detector reads only observable
telemetry. The Compose gap (§6.3) is now **covered in CI** by a
`docker compose config/build/up` + health/API smoke-test job.

---

## 2. Problems found (with evidence)

### 2.1 Packaging / configuration

- **Unpinned `requirements.txt` + a NumPy/Matplotlib conflict.** The declared
  runtime dependencies were not reproducible and included heavy packages
  (`numpy`, `pandas`, `matplotlib`) that the backend does not import.
- **Duplicate/fragmented configuration.** `backend/settings.py`, `backend/config.py`,
  and `backend/config/` coexisted; `backend/database.py` and `backend/app.py`
  shadowed the real `backend/database/` package and `backend/app/` package.
- **Unsafe defaults for production.** No validation prevented starting with the
  placeholder `SECRET_KEY`, `DEBUG=true`, wildcard CORS/hosts, or SQLite.

### 2.2 Backend correctness

- **Mutable default timestamps** in `backend/app/schemas/response.py`
  (`datetime.now()` evaluated once at import).
- **Datetime import errors** across `backend/models/*` (relying on removed shims).
- **Multiple, unrelated `DigitalTwinManager` instances** across API modules, so
  different endpoints mutated different simulator state.
- **Weak request validation** — several endpoints accepted unvalidated bodies,
  and unbounded lists/scenario sizes could exhaust memory.
- **WebSocket lifecycle** — connections not cleaned up reliably; no size guard.

### 2.3 Security

- **Direct training-label leakage into the detector.** `_check_ghost_pattern`
  read scenario ground-truth fields (`malicious`, `credential_label`), so
  detection was partly reading the answer key.
  (Now separated; see §3.3. A residual *name-token* heuristic remained — this was
  **fully removed in Phase 2**, see §9.1.)
- **Weak authentication/authorization.** The API and WebSocket stream were open
  on any reachable network, with no rate limiting or request-size bounds
  (**fixed in Phase 2**, see §9.3).
- **Ledger was not tamper-evident.** Records were stored without linkage, so
  silent edits/deletions were undetectable.

### 2.4 Research integrity

- **Ground truth and detector output were conflated** when recording detections,
  so precision/recall/F1 could not be interpreted.
- **Zero-denominator handling** for precision/recall/F1/FPR was inconsistent.
- **No reproducibility metadata** — runs were not seeded or labelled; exports
  did not record seed/config/version.
- **Metrics were not marked as synthetic**, so simulation output could be
  mistaken for validated results.

### 2.5 Frontend

- **Fabricated research data.** `ResearchConfiguration.tsx`,
  `ResearchReportGenerator.tsx`, and parts of the charting pages generated
  numbers with `Math.random()` / fixed constants instead of reading the backend.
- **Backend URL hardcoded** to `ws://localhost:8000`; REST relied on relative
  `/api` with no dev proxy (404s in dev).
- **Field-name mismatch with the backend** — pages read `detection_metrics`,
  `trust_metrics.average_score`, `verification.average_time`,
  `attack_defense_metrics`; the backend exposes `detection_accuracy`,
  `confusion_matrix`, `trust.average_trust`, `verification.*`,
  `attack_defense`. Charts silently showed zeros/undefined.
- **Unsupported/misleading claims** in generated reports: "blockchain-based
  append-only ledger", "distributed orchestrator", "sub-millisecond verification",
  "linear scalability", hardcoded "High-Risk Devices: 0".
- **Build was broken**: `tsconfig.json` had an invalid `ignoreDeprecations`
  value; `@types/react` / `@types/react-dom` were missing (1,261 type errors);
  dynamic Tailwind classes such as `bg-${color}-500` do not compile under JIT
  (invisible styling).

### 2.6 Deployment / hygiene

- `backend/Dockerfile` copied `./backend` under a `./backend` build context
  (broken path), installed from `requirements.txt`, and ran as root.
- `frontend/Dockerfile` used EOL Node 18 and `npm ci --silent || true`
  (swallowed install failures).
- CI installed from `requirements.txt`; pre-commit used black/isort/flake8
  alongside a ruff config.
- A stray UTF-16 build log, `frontend/build.out`, was present.

---

## 3. Changes made

75 tracked files changed. The raw diff is `+12,518 / −11,726`, but ~10.5k of
those lines are CRLF→LF normalisation (see §3.6); ignoring CR-at-EOL the real
**content** change is 70 files, `+1,994 / −1,202`. Plus 19 new files (tests,
docs, `uv.lock`, `.gitattributes`, `.editorconfig`, `.dockerignore`, and new
frontend modules).

### 3.1 Packaging (`pyproject.toml`, `uv.lock`)

- Single authoritative PEP 621 `pyproject.toml`; `requires-python = ">=3.12"`;
  `[tool.uv] package = false`; dev deps in `[dependency-groups] dev`.
- Removed unused runtime deps (`numpy`, `pandas`, `matplotlib`, `python-dotenv`).
  The dev dependency is now **`httpx2`** (not `httpx`): Starlette ≥ 1.x makes
  `httpx2` the supported `TestClient` backend and deprecates `httpx`, which
  previously emitted `StarletteDeprecationWarning` on every test run. `httpx` is
  only an optional FastAPI extra (`standard`/`all`), so it is safe to drop. This
  **resolves the NumPy/Matplotlib conflict by removal** rather than by pinning.
- Deleted `requirements.txt`. `uv lock` + `uv sync` regenerate reproducibly.

### 3.2 Configuration & startup

- **`backend/settings.py`**: central, validated settings (app name/version,
  environment, secret, hosts, CORS, DB URL, resource limits, `random_seed`,
  `app_version`) with a `model_validator` that **refuses to start in
  `production`** with placeholder secrets, `DEBUG`, wildcard CORS/hosts, or
  SQLite.
- **`backend/app/__init__.py`**: FastAPI lifespan (startup/shutdown),
  `TrustedHostMiddleware`, validated CORS.
- **`backend/app/api/`**: all route modules now share one manager via
  `get_manager()` (singleton in `backend/digital_twin/manager.py`).
- **`backend/app/schemas/requests.py`** (new): validated request models;
  `ScenarioRequest` gained an optional `seed`.
- Deleted shadow/dead modules: `backend/database.py`, `backend/config.py`,
  `backend/config/`, `backend/app.py`, and the bundled Windows venv `.venv313`.

### 3.3 Security

- **Detector de-leakage** (`backend/security/orchestrator.py`): `_check_ghost_pattern`
  no longer reads `malicious` / `credential_label`; the separation is documented
  at the call site. *Residual:* a name-token heuristic
  (`ghost/sybil/attacker/copy/clone/...`) that overlaps with the scenario
  generator's vocabulary — documented as a known weakness, not fixed.
  **Superseded in Phase 2:** the heuristic was deleted entirely and replaced by
  `GhostDetector`, which consumes only an observable `Observation` (§9.1).
- **Tamper-evident ledger** (`backend/security/ledger/sharded_ledger.py`):
  per-shard SHA-256 hash chain (`prev_hash` / `entry_hash`) with
  `verify_integrity()`, exposed at `GET /api/v1/security/ledger/integrity`.
  Explicitly documented as a local, single-node log — **not** a blockchain.
- **WebSocket hardening** (`backend/app/api/v1/ws.py`,
  `backend/app/websocket/manager.py`): size guard, orderly cleanup, bounded
  broadcast state.

### 3.4 Research integrity

- **`record_detection` joins and packets** now pass ground truth
  (`is_ghost`) and detector output (`detected_as_ghost`) as separate arguments.
- **`analytics_engine.py`**: correct TP/FP/TN/FN, precision/recall/F1/FPR with
  explicit zero-denominator handling; `metric_source: "simulation"`;
  `run_metadata` (seed, scenario, software version) via `set_run_metadata()`.
- **Reproducibility**: `SecurityOrchestrator(seed=…)` / `reset(seed=…)`;
  `DigitalTwinManager.run_scenario(seed=…)` seeds the ghost engine and proximity
  noise; `MAX_SCENARIO_DEVICES = 1000` bounds user input.

### 3.5 Frontend

- **`src/lib/config.ts`** + **`src/vite-env.d.ts`**: backend URL resolution via
  `VITE_API_BASE_URL` / `VITE_WS_URL`; `vite.config.ts` proxies `/api`
  (with `ws: true`) to `VITE_API_PROXY_TARGET` (default `http://localhost:8000`).
- **`src/lib/metrics.ts`** (new): `extractDetectionMetrics` / `extractTrust` /
  `extractVerification` normalise the **real** backend schema, so dashboards
  render real numbers (or zeros), never invented ones.
- **`useWebSocket.tsx`**: single connection, exponential backoff + jitter,
  `maxRetries`, stable handler ref, cleanup on unmount, explicit `reconnect()`.
- **`ResearchConfiguration.tsx`**: runs real seeded backend scenarios; shows
  real metrics + run metadata; error state; simulated-data label.
- **`AnalyticsCharts.tsx`**: reads real detection/trust/verification metrics via
  the normaliser; **confusion matrix now uses real TP/TN/FP/FN**; static Tailwind
  tones replace non-functional dynamic classes.
- **`ResearchReportGenerator.tsx`**: honest report (data-source note,
  limitations section); removed blockchain/distributed/sub-millisecond/
  linear-scalability claims; uses real fields.
- **`PresentationMode.tsx` / `ExportSystem.tsx`**: fixed wrong metric paths;
  exports include a "Data Source & Limitations" section.
- **Build fixed**: rewrote `tsconfig.json`; added
  `@types/react@18.3.12` + `@types/react-dom@18.3.1`; **type errors 1,261 → 0**;
  `npm run typecheck` and `npm run build` added and pass.
- **Dependency upgrades (security, tested)**:
  - `react-router-dom` 6.30.6 → **7.18.4** — fixes 2 *moderate* advisories
    (open-redirect via backslash in `<Link>`/`useNavigate`, and an SSR
    `deserializeErrors()` issue). **No 6.x patch exists**, so the fix requires
    v7; the app uses only `BrowserRouter`/`Routes`/`Route`/`NavLink` (no data
    routers, no SSR), so the migration was verified by typecheck + build +
    runtime, not merely assumed.
  - `vite` 5.4.21 → **6.4.4** and `@vitejs/plugin-react` 4.3.2 → **4.7.0** —
    fixes the Vite dev-server path-traversal advisory, the Windows-only
    dev-server advisories, and the `esbuild` advisory (Vite 6.4.x pins
    `esbuild ^0.25.0`, above the `<=0.24.2` vulnerable range).
  - Result: **production audit (`npm audit --omit=dev`) = 0 vulnerabilities**;
    the 7 remaining findings are dev-only (see §6).
- **Blocked npm install script (assessed, deliberately not approved):** npm 12
  blocks `esbuild@0.25.12`'s `postinstall` (`node install.js`). It is not needed
  in this environment — the platform binary is supplied by the optional
  `@esbuild/linux-x64` dependency, and `npm ci`, `typecheck`, and `build` all
  succeed with the script left blocked. No package install scripts were approved.

### 3.6 Deployment, CI, tooling, docs

- **`backend/Dockerfile`**: build context = repo root; installs from `uv.lock`
  (`uv sync --frozen --no-dev`); runs as non-root (`appuser`); healthcheck.
- **`frontend/Dockerfile`**: Node 22, `npm ci` (no swallowed failures).
- **`docker-compose.yml`**: correct contexts, env, healthchecks, `node_modules`
  volume, named data volume.
- **CI** (`.github/workflows/ci.yml`): uv-based backend lint+test, frontend
  typecheck+build, non-blocking dependency audit.
- **pre-commit** now uses ruff only; removed `.flake8`; removed stray
  `frontend/build.out`; added `.dockerignore` (root + frontend).
- **Line-ending / whitespace hygiene**: the tree mixed CRLF and LF, so
  `git diff --check` reported **1,116** "trailing whitespace" errors (Git treats
  the CRLF `\r` on added lines as trailing whitespace). Added `.gitattributes`
  (`* text=auto eol=lf` plus binary markers) and `.editorconfig`; normalised the
  changed text files to **LF** and removed whitespace-only lines. `git diff
  --check` is now **clean (0)**. This is a genuine, git-visible whole-file
  line-ending change for the formerly-CRLF files; ignoring CR-at-EOL the
  semantic diff is unchanged.
- **`backend/Dockerfile`** now creates `/data` and `chown`s it to `appuser`, so
  the Compose named volume at `/data` is writable by the non-root user
  (previously a freshly created named volume would be root-owned and the SQLite
  database uncreatable).
- **Docs**: `docs/ARCHITECTURE.md` (new), this audit, updated `README.md`,
  `.env.example` (backend + frontend), and corrected the ledger section of
  `SECURITY_FRAMEWORK_IMPLEMENTATION.md` ("Distributed Storage" → tamper-evident
  hash-chained log).

### 3.7 Tests added

`tests/conftest.py` (isolated temp SQLite, `ENVIRONMENT=test`) plus:
`test_ledger_integrity.py` (tamper detection), `test_analytics_metrics.py`
(precision/recall/F1/FPR + zero-denominator), `test_research_integrity.py`
(ground-truth/detector separation + seed reproducibility),
`test_api_validation.py` (422 on bad input), `test_settings_validation.py`
(production guards). **34 tests pass** (Phase 1).

Phase 2 added `test_ghost_detector.py`, `test_detection_evaluation.py`, and
`test_api_security.py`, and rewrote `test_security_orchestrator.py` /
`test_secureaccess_access_control.py` / parts of `test_research_integrity.py` to
exercise observable-feature detection. **Total: 94 tests pass** (see §9.7).

---

## 4. Honesty: explicit non-claims

These are **simulated** and documented as such in code and docs:

- **Cryptography** — `SimulatedLatticeCrypto` produces synthetic keys/signatures;
  it provides no security and only models timing/call structure. It implements
  the `IPostQuantumCrypto` interface so a real `liboqs-python` backend can drop in.
- **Proximity** — distance is a modelled path delay + injected noise, not
  hardware ranging; not proof of physical presence.
- **Ledger** — local, single-node, hash-chained, tamper-evident; no replication,
  no consensus, no blockchain.
- **Metrics** — computed against the simulator's synthetic ground truth. Phase 2
  removed the name-token leakage (§9.1) and evaluates the detector on scenario
  distributions (including deliberately hard hold-outs) that were *not* used to
  design the rules; the reported precision/recall still characterise the
  **simulator**, not real-world performance (see §9.2 for exact numbers and the
  0%-recall hold-out).

---

## 5. Checks performed (exact commands & results)

Environment: Python 3.14.7 + `uv`; Node 26.11.1 + npm 12.2.0; Docker 29.9.0.

Backend:

| Command | Result |
|---------|--------|
| `uv lock && uv sync` | ✅ resolved 38 packages; installed/updated cleanly |
| `uv run ruff check .` | ✅ All checks passed |
| `uv run pytest` | ✅ **34 passed** (no warnings) — Phase 1; **94 passed** after Phase 2 (§9.7) |
| `uv run pytest -o addopts="" -v` | ✅ 34 passed — includes ledger tamper **and deletion** detection, ground-truth/detector separation, seeded reproducibility, API bounds, production config guards |
| `uv run python -W error -c "from fastapi.testclient import TestClient"` | ✅ imports cleanly; `TestClient` backend = `httpx2` (warning resolved) |
| `uv run python -c "from backend.main import app"` | ✅ app imports |
| `uv run pytest --cov=backend` | ✅ total ≈60% (orchestrator 88%, analytics 79%, ledger 68%, manager 69%, settings 97%; `api/v1/security.py` 36%) |

Repository hygiene:

| Command | Result |
|---------|--------|
| `git diff --check` | ✅ **0** whitespace errors (was **1,116** CRLF-induced) |

Frontend:

| Command | Result |
|---------|--------|
| `npm ci` | ✅ 149 packages installed from lockfile |
| `npm run typecheck` (`tsc --noEmit`) | ✅ 0 errors |
| `npm run build` (`vite build`) | ✅ 1,941 modules → `dist/` (Vite 6.4.4) |
| `npm audit --omit=dev` | ✅ **0 vulnerabilities** (production) |
| `npm audit` | ⚠️ **7** (2 moderate, 5 high) — dev-only Tailwind 3 chain (see §6) |

Docker (daemon available; **Compose plugin NOT available**). Images were built
and run directly as a stand-in for `docker compose`:

| Command | Result |
|---------|--------|
| `docker build -f backend/Dockerfile -t qshield-backend:verify .` | ✅ built (python:3.12-slim, `uv sync --frozen --no-dev`, non-root) |
| `docker run … qshield-backend:verify` | ✅ `/api/v1/health` → **200**; ran as uid 10001; `/data` volume writable (`qshield_twin.db` created); healthcheck `healthy`; `/api/v1/status`, `/api/v1/devices`, `/api/v1/security/ledger/integrity` → 200; `docker stop` → **ExitCode 0** (clean shutdown) |
| `docker build -f frontend/Dockerfile -t qshield-frontend:verify ./frontend` | ✅ built (node:22-alpine, `npm ci`) |
| `docker run … + curl :15173/` | ✅ `HTTP 200`, `<title>QShield Twin</title>` |
| `curl :15173/api/v1/health` (Vite proxy → backend) | ✅ **200** from backend — frontend↔backend integration works |
| `docker compose config` / `docker compose up` | ❌ **not executed** — Compose v2 plugin absent |

All verification containers, volumes, networks, and images were removed
afterwards. `git diff` contains **no** staged changes, secrets, or generated
artifacts (`dist/`, `node_modules/`, `.venv/` are ignored and untracked).

---

## 6. Remaining risks & limitations

1. **Detector generalisation is only demonstrated on synthetic scenarios.**
   The name-token leakage is fixed (§9.1), but the reported precision/recall are
   measured against *simulated* ground truth in controlled scenarios. On a
   deliberately hard, sub-threshold ("stealth") holdout the detector's recall is
   **0%** (§9.2) — an honest limitation, not a solved problem.
2. **Coverage 60%**, concentrated in `api/v1/security.py` (36%) — many endpoints
   are untested; several endpoints return HTTP 200 with `status:"error"` (kept
   for contract compatibility).
3. **Compose not executed locally.** The Compose v2 plugin is unavailable, so
   `docker compose up` was not run here. It is now validated **in CI**
   (`docker compose config`, `build`, `up`, health + API smoke test — §9.8);
   the backend image was also rebuilt and smoke-tested directly after the Phase 2
   hardening (dev-open and token-enforced modes, §9.3).
4. **Frontend advisories (dev-only).** `npm audit` reports **7** (2 moderate,
   5 high), all in the Tailwind 3 build chain: `braces` → `chokidar` /
   `micromatch` → `fast-glob`, `postcss-nested` → `postcss-selector-parser`, and
   `tailwindcss` itself. `braces` has **no patched release**
   (`first_patched_version: null`, CVE-2026-93687), so it cannot be fixed
   without removing Tailwind 3; the only npm-offered fix is Tailwind **4**
   (major). These packages run only at build time on trusted inputs and are
   **not shipped in `dist/`**; the production audit (`--omit=dev`) is clean.
   Mitigation: keep Tailwind builds off untrusted input; plan a tested Tailwind 4
   migration.
5. **Line-ending migration is partial by design.** Only *changed* files were
   normalised to LF; unmodified tracked files remain CRLF until next touched.
   `.gitattributes` makes LF the repository convention, so a one-time
   `git add --renormalize .` at commit time completes the migration.
6. **Authentication is a single shared token, and rate limiting is in-process.**
   Phase 2 added an opt-in `API_TOKEN`, per-client rate limits and request-size
   limits (§9.3). The secret is held **server-side** (the Vite dev proxy in
   development, a reverse proxy in production — §9.5) and is never shipped to the
   browser, but it is still a **single shared deployment-level gate, not user
   authentication**: there is **no identity/RBAC layer**, and the in-process
   limiter is per-instance (it does not coordinate across workers/replicas and is
   not an edge-grade rate limiter). It is adequate for a single-service research
   deployment, not a substitute for a gateway.
7. **Frontend `any` usage** remains in parts of the dashboard; runtime-safe but
   not fully typed.
8. **No browser/E2E tests** for the frontend (typecheck + build + a manual proxy
   smoke test only).
9. **Single-process simulator**; no concurrency/perf benchmarks.

---

## 7. Next three highest-value improvements

1. **Replace the token heuristic with a principled detector** (feature-based
   scoring on proximity error, signature failures, packet behaviour) and
   re-measure metrics **without** sharing vocabulary with the scenario
   generator — closing the integrity gap in §6.1.
   ✅ **Done in Phase 2** (§9.1–§9.2).
2. **Raise backend coverage to ≥80%**, focusing on `api/v1/security.py` and
   `network.py`, and adopt a typed frontend API client to eliminate the
   remaining `any`s and field-mismatch class of bugs.
3. **Complete deployment verification and clear the remaining advisories**:
   run `docker build` + `docker compose up` in CI (the images already build and
   run individually here), and migrate Tailwind 3 → 4 in a dedicated, tested
   change to clear the 7 dev-only advisories; add API authentication + rate
   limiting before any non-local exposure.
   ◑ **Partially done in Phase 2:** Compose build/up/health/API smoke test added
   to CI (§9.8), and API authentication + rate limiting + request-size limits
   implemented and tested (§9.3). Tailwind 4 migration still outstanding.

---

## 8. How to reproduce

```bash
uv sync
uv run ruff check .
uv run pytest -q
uv run uvicorn backend.main:app --reload         # backend :8000

cd frontend && npm ci && npm run typecheck && npm run build
npm run dev                                       # frontend :5173 (proxies /api)

./scripts/start_backend.sh
./scripts/start_frontend.sh
```

---

## 9. Phase 2 — Detection intelligence & security hardening

This phase addresses §6.1 (detector integrity) and §6.6 (API auth/abuse
protection), and closes the §6.3 Compose gap in CI. All changes are additive and
keep the Phase-1 green state.

### 9.1 Feature-based ghost detector (`backend/security/detection/`)

The name-token heuristic (`_check_ghost_pattern`) and the two helpers that
fabricated the "measured" position from the detector's own output
(`_infer_measured_position`, `_is_suspicious_packet`) were **deleted**. The
orchestrator now derives an `Observation` from telemetry a deployment can
measure and scores it with `GhostDetector` (version `ghost-detector/2.0`):

| Feature | Observable source | Reliability α |
|---|---|---|
| Proximity error | proof-of-proximity measured vs. claimed position | 0.90 |
| Signature failure ratio | accumulated auth/verification failures | 0.85 |
| Identity cluster size | distinct identities at one measured origin | 0.90 |
| Credential reuse | one credential fingerprint across identities | 0.60 |
| Packet rate / size | traffic volume | 0.50 / 0.45 |
| Sustained low trust | trust-engine score | 0.30 |

- **No label leakage.** The `Observation` contract contains only observable
  fields; names, ids, `device_type`, `malicious`, `legitimate`,
  `credential_label`, `attacker_id` and the ghost-engine registry are never read.
  A regression test feeds an adversarially-named (``ghost-123``) but benign
  device and asserts it is **not** flagged.
- **Transparent and deterministic.** Evidence is combined with a **noisy-OR**
  (`score = 1 − ∏(1 − αᵢ·subᵢ)`) so one high-reliability indicator can flag alone
  while weak ones must corroborate. Every decision carries
  `score`, `features`, `contributions` and human-readable `reasons`, recorded in
  the ledger and analytics.
- **Circularity removed.** The measured position now comes from the observation
  (or a benign default), never from the detector's verdict, so the proximity
  engine and the detector no longer feed each other.
- **Dependency-free.** Pure Python (`math`/`threading`); no ML, no NumPy/pandas.

Integration points: `SecurityOrchestrator.receive_join`/`receive_packet`,
`AnalyticsEngine.record_detection` (now stores `score`, `detector_version`,
`reasons`, `observed`), `DigitalTwinManager.run_scenario` (records
`detector_version` / `detector_threshold` in run metadata), and the
access-control demo builder, which now emits **neutral-named** devices
distinguished only by observable telemetry.

### 9.2 Independent evaluation (`evaluation.py`, `scenarios.py`, `baseline.py`)

A deterministic scenario generator (`build_scenario`/`build_suite`) produces
observation streams with **neutral names** and separate ground-truth labels, for
attack families `clone`, `sybil_herd`, `spoof`, `traffic_abuse`, `auth_failure`,
plus `legit`. Ground truth is held out and used only for scoring. Three suites
are evaluated across seeds `[1, 7, 42, 1337, 9001]`; a `NameTokenBaseline`
reproduces the old heuristic for honest comparison.

Reproduce with `uv run python -m backend.security.detection.run_evaluation`. Exact
results (synthetic scenarios):

| Suite | Devices | TP | FP | TN | FN | Precision | Recall | F1 | FPR |
|---|---|---|---|---|---|---|---|---|---|
| Tuning | 1,510 | 260 | 1 | 1,249 | 0 | 0.996 | **1.000** | 0.998 | 0.0008 |
| Hold-out (separable) | 1,155 | 227 | 0 | 925 | 3 | 1.000 | **0.987** | 0.993 | 0.000 |
| Hold-out **hard** (stealth, sub-threshold) | 265 | 0 | 0 | 225 | 40 | 0.000 | **0.000** | 0.000 | 0.000 |
| Baseline (name-token) on hold-out | 1,155 | 0 | 0 | 925 | 230 | 0.000 | **0.000** | 0.000 | 0.000 |

Interpretation, stated plainly:

- On **separable** scenarios the detector recovers almost everything with
  negligible false positives (hold-out recall 0.987; the 3 misses are the hardest
  `spoof` cases).
- The `holdout_hard` suite keeps every feature **below threshold**; the detector
  honestly reports **0% recall** there. Threshold/rule detectors cannot catch
  adversaries who stay within "normal" envelopes — this is a known limitation,
  not hidden.
- The `NameTokenBaseline` scores **0% recall** once names are neutral, confirming
  the Phase-1 numbers were an artifact of vocabulary leakage.

Metrics are zero-denominator safe (`Metrics.precision/recall/f1/accuracy/fpr`),
and the report records version, seeds and metric definitions. The harness also
tracks a separate `unknown` bucket for devices the detector could not decide;
it is excluded from TP/FP/TN/FN. The generated evaluation scenarios supply full
telemetry to every device, so `unknown = 0` in the table above — the unknown
path is exercised by dedicated unit/integration tests instead (see §9.6).

### 9.3 API & WebSocket hardening

- **Authentication (`backend/app/core/security.py`).** An opt-in shared token
  (`API_TOKEN`) protects the state-changing/sensitive routers (`devices`,
  `simulation`, `network`, `statistics`, `security`) via `require_api_token`.
  Accepted forms: `X-API-Token`, `Authorization: Bearer …`; the WebSocket accepts
  a `?token=` query parameter (browsers cannot set WS handshake headers).
  Comparison is constant-time. **Unset token ⇒ open** (local development);
  **production requires a token** (enforced by `Settings`). The resolved settings
  live on `app.state.settings` so request and WS handlers agree.
- **Rate limiting (`middleware/rate_limit.py`).** Per-client fixed-window
  limiter (default `600/60s`), health endpoints exempt, returns `429` +
  `Retry-After`. Documented as in-process/per-instance, **not** edge-grade.
- **Request-size limit (`middleware/max_body.py`).** Rejects bodies whose
  `Content-Length` exceeds `MAX_REQUEST_BYTES` (default 1 MB) with `413`; chunked
  bodies fall back to Pydantic bounds (documented).
- **WebSocket (`api/v1/ws.py`, `websocket/manager.py`).** Token check and a
  concurrent-connection cap (`MAX_WS_CONNECTIONS`, default 50) are enforced
  *before* accept (`1008` / `1013`); the existing max-frame guard remains.
- **Config (`settings.py`, `.env.example`).** New validated settings
  (`api_token`, `rate_limit_*`, `max_request_bytes`, `max_ws_connections`) and a
  production guard requiring `API_TOKEN`.
- **Frontend token exposure (fixed in §9.5).** Earlier Phase-2 work added an
  optional `VITE_API_TOKEN` in `lib/config.ts` (a `fetch` monkeypatch plus a
  `?token=` on the WebSocket URL). That is **unsafe by construction**: Vite
  inlines every `VITE_`-prefixed variable into the browser bundle, so the shared
  backend secret was published to every visitor. It has been removed and replaced
  with a server-side proxy that holds the secret (§9.5). Also fixed a
  field-mismatch class of bug: several pages read the security
  counters/trust from the **top level** of `/security/status`, but the backend
  nests them under `security`. A shared `extractSecurityCounters` /
  `extractTrust` helper in `lib/metrics.ts` now reads the correct path
  (tolerating the flat shape too), so the trust/counter stat cards and exported
  reports render real values instead of zeros. A backend contract test
  (`test_security_status_frontend_contract`) pins the shape the dashboard relies
  on.

**Not implemented (explicit):** identity/RBAC, per-route quotas, CSRF (the API is
token-based, not cookie-based), distributed/edge rate limiting, TLS termination.

### 9.4 Attack-campaign accounting & demo metric consistency

The ghost/Sybil campaign had two pre-existing metric bugs that became visible
once the detector became feature-based:

- `SecurityOrchestrator.start_attack` spawned ghost-engine nodes that never
  traversed the pipeline, so the new (observation-driven) detector never scored
  them and the campaign always reported `0%` detected — contradicting the
  confusion matrix.
- `record_attack` was called both on start (spawned) and on stop
  (spawned + detected), double-counting `ghosts_spawned` and incrementing
  `attacks_launched` twice per campaign.

Fixes:

- `start_attack` now feeds every spawned identity through `receive_join` with
  **observable** Sybil telemetry (one shared credential fingerprint, co-located
  spoofed proof-of-proximity measurements, failing signatures, elevated packet
  rate). The detector still decides; nothing labels the node as a ghost.
- A detection-only `AnalyticsEngine.record_detections` records detections once
  at stop, so a campaign is counted exactly once.
- `GhostEngine.stop_attack` recomputes `detected_count`/`detection_rate` from
  the `detected_at` markers immediately, instead of waiting for the background
  thread to reach the end of its duration.
- The demo scenario (`run_scenario`) derives its attack summary from the actual
  detector outcomes (capped at the number of distinct ghost identities) rather
  than the vestigial ghost-engine loop, so `attack`, `attack_defense` and the
  confusion matrix now agree.

Regression coverage: `test_access_control_demo_and_api_endpoints` asserts
`detected_count == ghost_count`, and
`test_attack_campaign_statistics_reflect_detections` pins single-counting
(`attacks_launched == 1`, `ghosts_spawned == ghosts_detected == count`).

### 9.5 Final-review fix — server-side API token (no secret in the browser)

**Root cause.** Phase-2 hardening put an optional shared backend secret in a
`VITE_`-prefixed variable (`VITE_API_TOKEN`) and had the browser attach it to
requests (`installApiAuth()` monkeypatched `window.fetch`; `wsUrl()` appended
`?token=`). Vite statically inlines **every** `VITE_`-prefixed variable into the
client bundle, so the shared secret was published to every visitor — a
`VITE_`-prefixed value is public by definition and must never be treated as a
secret.

**Architecture chosen — server-side proxy holding the secret.** The browser no
longer holds or sends any token. A server-side component injects the
`X-API-Token` header when forwarding to the backend:

- **Development:** the Vite dev-server proxy (`frontend/vite.config.ts`) reads a
  *non-`VITE_`* variable `QSHIELD_API_TOKEN` (from the environment or
  `frontend/.env.local`) and injects the header on both `proxyReq` and
  `proxyReqWs`, so `/api` REST calls and the `/api/v1/ws/stream` upgrade are
  authenticated. The token lives only in the Node process.
- **Production:** a reverse proxy (nginx/Caddy/etc.) serves the static `dist/`
  and injects the same header. Documented in `docs/ARCHITECTURE.md`.
- **Local dev:** unchanged and frictionless — leave `API_TOKEN`/`QSHIELD_API_TOKEN`
  unset and the backend stays open.

This is explicitly a **deployment-level gate, not user authentication**: it stops
anonymous public access to the API but provides no per-user identity, scoping or
RBAC (see limitations §7).

Changes: `frontend/src/lib/config.ts` (token removed; `API_TOKEN`, `authHeaders`
and `installApiAuth` deleted; `wsUrl()` no longer appends a token),
`frontend/src/main.tsx` (call removed), `frontend/src/vite-env.d.ts`, the root
and `frontend/.env.example`, `docker-compose.yml` (backend gets `API_TOKEN`,
frontend gets `QSHIELD_API_TOKEN`, both from `${API_TOKEN:-}`), and CI.

Regression coverage:
- `tests/test_frontend_secret_isolation.py` — static guards: no
  `import.meta.env.VITE_*TOKEN` access, no `X-API-Token` literal in client source,
  and the Vite config reads only the non-`VITE_` token variable.
- `frontend/scripts/check-bundle-secrets.mjs` (`npm run check:secrets`, wired
  into the CI frontend job) — builds the production bundle with a sentinel placed
  in **both** `VITE_API_TOKEN` and `QSHIELD_API_TOKEN` and fails if the sentinel
  appears anywhere in the output.

**Evidence.** The scanner was verified to have teeth: a throwaway
`import.meta.env.VITE_API_TOKEN` reference made Vite inline the sentinel into
`dist/assets/*.js` (detected), while the shipped code produces a clean bundle.
End-to-end proxy test (dev server + backend, `API_TOKEN` set):
direct backend without token → **401**; direct with token → **200**; through the
Vite proxy with the browser sending **no** token → **200**; WebSocket through the
proxy → `ack:ping` (injected header accepted) while direct unauthenticated WS is
rejected.

### 9.6 Final-review fix — missing telemetry is never silently benign

**Root cause.** `SecurityOrchestrator._extract_observation` fabricated benign
defaults when telemetry was absent (`measured_pos = claimed + small noise`,
`credential_fingerprint = f"cred-{device_id}"`), and the detector treated absent
signals as "no evidence" → score 0 → pass. An identity with **no** verifiable
telemetry was therefore accepted, and such events were counted as *true
negatives* in analytics. Absence of evidence was being reported as evidence of
innocence.

**Fix — explicit data-quality outcome.** `DetectionOutcome` now carries a
`status` (`ok` | `insufficient_data` | `stale` | `malformed` | `contradictory`)
and an `is_unknown` property (`not is_flagged and status != "ok"`). A *positive*
(flagged) decision is actionable on its own, so it is always `ok`; a *negative*
decision is only `ok` when the telemetry is valid, fresh, self-consistent and
plentiful enough (`min_observable_signals`, default 2 independent signal
families).

Safe behaviour, by degradation mode:

| Telemetry | Detector status | Sensitive join | Non-sensitive join |
|---|---|---|---|
| Missing / too few signals | `insufficient_data` | `challenge` (not accepted) | `monitor` (accepted, flagged unknown) |
| Present but invalid (bad type, negative volume, out-of-range trust, non-finite) | `malformed` | `challenge` (not accepted) | `monitor` |
| Newest sample older than `max_observation_age_seconds` | `stale` | `challenge` (not accepted) | `monitor` |
| Failed signature + high trust, or signature verification flapping | `contradictory` | existing deny kept, else `challenge` | existing deny kept, else `monitor` |

- The detector validates each field independently; a present-but-invalid field
  counts as malformed rather than being dropped, and `is_unknown` is surfaced in
  the API result (`detection_status`, `detection_unknown`) and ledger evidence.
- `receive_join` escalates a would-be **allow** to `challenge` for
  security-sensitive access-control joins (`spawn_access_control_device` sets
  `security_sensitive=True`). It **never weakens** an existing `reject`/
  `blacklist`, so unknown telemetry cannot silently admit an identity.
- Analytics: `record_detection(observed=...)` excludes unknown events from the
  confusion matrix (so they are **never** true negatives) and reports them in a
  new `observation_coverage` block and `detector.unknown_detections`. CSV export
  gains an `observed` column. The evaluation harness `Metrics` gains a separate
  `unknown` bucket, likewise excluded from TP/FP/TN/FN.

Regression coverage: `tests/test_detector_unknown.py` (benign-ok, missing,
partial, malformed, stale, contradictory, flapping, strong-single-signal, and
never-observed), `tests/test_access_control_unknown.py` (sensitive
missing/malformed/contradictory → not accepted; sensitive sufficient-benign →
accepted; non-sensitive unknown → monitor; unknown join and packet not counted as
TN), plus analytics/evaluation tests (`test_unknown_detections_are_not_counted_as_true_negatives`,
`test_observation_coverage_reports_observed_ratio`,
`test_unknown_outcomes_are_excluded_from_confusion_matrix`).

**Honesty.** The offline evaluation scenarios always supply full telemetry, so
they exercise the *decision* path, not the unknown path; the unknown handling is
verified by unit/integration tests, not field-validated.

### 9.7 Tests added

`test_ghost_detector.py` (benign/spoof/signature/cluster/credential behaviours,
name-independence, determinism, threshold config, reset),
`test_detection_evaluation.py` (zero-denominator metrics, scenario determinism and
neutral names, detector-vs-baseline, per-attack reporting, honest hard-suite
recall, CLI report serialisation, unknown-not-TN),
`test_detector_unknown.py` and `test_access_control_unknown.py` (degraded-telemetry
handling, §9.6), `test_frontend_secret_isolation.py` (no client-side token,
§9.5), and `test_api_security.py` (401 without token, accepted header forms,
health open, dev-open, `429` rate limit + health exempt, `413` body limit,
WebSocket 1008/1013 and open-when-unconfigured). Outdated name-based tests were
rewritten to be observable-feature-based, and `test_api_endpoints.py` gained a
`test_security_status_frontend_contract` that pins the `/security/status` shape
the dashboard renders.
**Total: 94 backend tests pass.**

### 9.8 CI (`.github/workflows/ci.yml`)

Added a `docker-compose` job that runs `docker compose config`, `build`, `up`,
waits for backend health, smoke-tests `/api/v1/health`, `/version` and
`/security/status`, checks the frontend is reachable, dumps logs on failure, and
always tears the stack down — closing the local Compose-plugin gap (§6.3). The
frontend job also runs `npm run check:secrets` (§9.5).

### 9.9 Phase 2 verification (exact)

| Command | Result |
|---|---|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run pytest -q -o addopts=""` | ✅ **94 passed** |
| `uv run python -m backend.security.detection.run_evaluation` | ✅ ran; numbers in §9.2 (all suites `UNKNOWN=0`) |
| `cd frontend && npm run typecheck` | ✅ 0 errors |
| `cd frontend && npm run build` | ✅ 1,941 modules (Vite 6.4.4), clean bundle |
| `cd frontend && npm run check:secrets` | ✅ no API token in bundle (sentinel not found); guard proven to catch a real inlined leak |
| Vite dev-proxy integration (backend `API_TOKEN` set) | ✅ direct no token → **401**, direct with token → **200**, via proxy no token → **200**, WS via proxy → `ack:ping` |
| `docker build -f backend/Dockerfile -t qshield-backend:hardened .` | ✅ built |
| `docker run … (dev, no token)` | ✅ `/api/v1/health` 200; access-control demo → TP=10, FP=0; detector `ghost-detector/2.0` |
| `docker run … -e API_TOKEN=…` | ✅ no/wrong token → **401**, correct token → **200**, health open → **200** |
| access-control demo scaled (100/300/500 legit × 20/50/80 ghost) | ✅ FP = **0** at every scale |
| `uvx pip-audit` | ✅ No known vulnerabilities |
| `cd frontend && npm audit --omit=dev` | ✅ 0 vulnerabilities (7 dev-only Tailwind-3 advisories remain, §6.4) |
| `POST /api/v1/security/attack/start` then `/stop` | ✅ `detection_rate=1.0`, `ghosts_detected == ghosts_spawned`, `defense_success_rate=1.0` |
| `uv run python -m backend.validation.teacher_demo` | ✅ Final Result: PASS (all six modules) |

No changes were committed. The Phase-1 baseline archive remains recoverable at
`/tmp/opencode/QShield-Twin-baseline-20261010-183255.tar.gz`.
