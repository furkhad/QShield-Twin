# QShield Twin — Deployment

This document describes the **production** deployment path added in this
milestone, and the honest limits of what it does and does not provide.

Two Compose files coexist and do not interfere with each other:

| File | Purpose | Frontend | Database | Source mounts |
|------|---------|----------|----------|---------------|
| `docker-compose.yml` | **Development.** Vite dev server + uvicorn with hot reload. | `npm run dev` | SQLite volume | yes |
| `docker-compose.prod.yml` | **Production.** Multi-stage static bundle behind nginx. | nginx + compiled `dist/` | PostgreSQL | none |

Nothing in this document is a claim that the application itself is a
production-grade security product — see the honesty notes in `README.md` and
`docs/ARCHITECTURE.md`.

---

## 1. Architecture

```text
                 host (loopback by default)
browser ─────────────────────────────────▶┌─────────────────────────────┐
   :8080                                  │ frontend (nginx:1.27-alpine) │
                                          │  • serves compiled dist/      │
                                          │  • SPA fallback               │
                                          │  • proxies /api/ ──┐          │
                                          │  • injects X-API-Token (server-│
                                          │    side, never in the bundle) │
                                          └────────────────────┼──────────┘
                                                    internal network
                                                               │
                                          ┌────────────────────▼──────────┐
                                          │ backend (python:3.12-slim)     │
                                          │  uvicorn, non-root uid 10001   │
                                          │  FastAPI + WebSocket           │
                                          └────────────────────┬──────────┘
                                                    internal network
                                                               │
                                          ┌────────────────────▼──────────┐
                                          │ db (postgres:16.4-alpine)      │
                                          │  named volume postgres-data    │
                                          └────────────────────────────────┘
```

* **Exposure.** Only the frontend publishes a port, and it binds to
  `127.0.0.1` by default. The backend (`:8000`) and PostgreSQL (`:5432`) are
  reachable only on the internal Compose network; no `ports:` are declared for
  them, so their host ports are not exposed.
* **Request flow.** The browser loads `/`, `/assets/*` from nginx. REST calls go
  to `/api/v1/...` and the event stream to `/api/v1/ws/stream`, both proxied by
  nginx to `http://backend:8000` over the internal network. nginx adds the
  `X-API-Token` header server-side, so the browser never holds the token.
* **Data flow.** PostgreSQL holds the SQLAlchemy schema
  (`devices`, `identity_claims`, `ledger_entries`, `trust_records`) in the
  `postgres-data` named volume. The security audit ledger and analytics are
  in-memory (see §7).

---

## 2. Required environment variables

Copy the template and fill it in:

```bash
cp .env.production.example .env.production
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | **yes** | Application secret. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `API_TOKEN` | **yes** | Shared deployment token. Backend requires it; the frontend proxy injects it. Generate with `secrets.token_urlsafe(32)`. |
| `POSTGRES_PASSWORD` | **yes** | Password for the application database user. Generate with `secrets.token_urlsafe(24)`. |
| `POSTGRES_DB` / `POSTGRES_USER` | no (defaults `qshield`/`qshield`) | Database name/user. |
| `ALLOWED_HOSTS` | **yes** | JSON array of hosts the backend accepts, e.g. `["localhost","127.0.0.1"]`. Must not contain `"*"`. |
| `QSHIELD_ALLOWED_HOSTS` | **yes** | Space-separated hosts the nginx edge accepts, e.g. `localhost 127.0.0.1`. |
| `QSHIELD_SERVER_NAME` | no (`_`) | nginx `server_name`; use the real hostname for a named deployment. |
| `CORS_ORIGINS` | no (`[]`) | JSON array. Browser traffic is same-origin, so this stays empty. Must not contain `"*"`. |
| `QSHIELD_BIND_ADDRESS` / `QSHIELD_FRONTEND_PORT` | no (`127.0.0.1` / `8080`) | Where the frontend is published. |
| `QSHIELD_IMAGE_TAG` | no (`local`) | Image tag to run (see §4/§5). |
| `LOG_LEVEL`, `RATE_LIMIT_*`, `MAX_*` | no | Tuning knobs with safe defaults. |

`SECRET_KEY`, `API_TOKEN` and `POSTGRES_PASSWORD` have **no defaults**: the
stack refuses to start if they are missing. They are supplied as *runtime*
environment variables — never as Docker build arguments — so they are not baked
into any image layer.

### Secure setup

* Keep `.env.production` out of version control (it is git-ignored) and readable
  only by the deploying user: `chmod 600 .env.production`.
* Prefer injecting secrets from a manager (Docker secrets, systemd
  `EnvironmentFile=`, Vault, cloud secret stores) rather than a plain file.
* Never pass these values to `docker build`/`--build-arg`, and never prefix them
  with `VITE_` (Vite would inline them into the public browser bundle).

---

## 3. Why PostgreSQL, and what actually changed

`backend/settings.py` already **refuses to start** in `ENVIRONMENT=production`
with a SQLite URL, so production needs a networked database. The original
repository had two gaps that made that posture unachievable:

1. **No driver.** No PostgreSQL driver was declared or locked, so importing the
   app with a `postgresql://` URL raised `ModuleNotFoundError: No module named
   'psycopg'`. Fixed by adding `psycopg[binary]` to `pyproject.toml` / `uv.lock`
   (SQLite paths never import it).
2. **No schema.** `init_db()` called `Base.metadata.create_all()`, but nothing in
   the application imported the model modules, so `Base.metadata` was empty and
   **zero tables** were created against any database. SQLite "worked" only
   because no request path reads or writes the SQLAlchemy models today (device
   state lives in memory). Fixed by importing `backend.models` in
   `backend/database/__init__.py` so the tables are registered before
   `create_all()` runs.

Both fixes were verified against a real PostgreSQL 16 server: with a
`postgresql+psycopg://` URL and `ENVIRONMENT=production`, `init_db()` creates
`devices`, `identity_claims`, `ledger_entries`, `trust_records`.

There are **no migrations** (no Alembic). Schema changes are applied by
`create_all()`, which only creates missing tables — it does not alter existing
ones. For a research deployment that is acceptable; a schema migration tool is a
follow-up item (§7).

---

## 4. Local build and run (maintainers and CI)

```bash
# 1. Build images with the exact registry names/tags (nothing is pushed).
scripts/build-prod-images.sh local

# 2. Configure secrets.
cp .env.production.example .env.production
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"     >> .env.production
python -c "import secrets; print('API_TOKEN=' + secrets.token_urlsafe(32))"      >> .env.production
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))" >> .env.production
# (or edit .env.production by hand and delete the duplicated empty lines)
chmod 600 .env.production

# 3. Start.
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 4. Smoke test.
curl -fsS http://127.0.0.1:8080/healthz                 # nginx up
curl -fsS http://127.0.0.1:8080/api/v1/health           # nginx -> backend
curl -o /dev/null -s -w '%{http_code}\n' http://127.0.0.1:8080/    # 200 (SPA)

# 5. Stop (keeps the database volume).
docker compose -f docker-compose.prod.yml --env-file .env.production down
```

`QSHIELD_IMAGE_TAG` defaults to `local`, which is exactly what
`scripts/build-prod-images.sh` produces, so step 2 needs no extra configuration
for a local run.

---

## 5. Pull and run published images (after a release exists)

No images have been published yet. Do not run `docker compose pull` before a
release has been pushed to GHCR — it will fail with "manifest unknown".

The intended sequence **once images are published** under
`ghcr.io/furkhad/qshield-twin-backend` / `ghcr.io/furkhad/qshield-twin-frontend`:

```bash
# Optional: authenticate if the packages are private.
echo "$GHCR_TOKEN" | docker login ghcr.io -u furkhad --password-stdin

cp .env.production.example .env.production   # fill in secrets, as in §4

# Pick the released version tag (not `local`).
export QSHIELD_IMAGE_TAG=0.2.0
docker compose -f docker-compose.prod.yml --env-file .env.production pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Because the local build script tags images with the same names, the Compose file
is identical for local and published images; only `QSHIELD_IMAGE_TAG` (and
optionally a `docker login`) differs. Publishing itself (GHCR workflow, tags,
provenance/SBOM, repo settings) is a **separate follow-up task** and is
deliberately not implemented here.

---

## 6. Health, restart and shutdown behaviour

| Concern | Behaviour |
|---------|-----------|
| Backend health | Image `HEALTHCHECK` polls `/api/v1/health`; Compose also uses `depends_on: service_healthy` so the frontend starts only once the backend is answering. |
| Database readiness | `db` uses `pg_isready`; the backend waits for `service_healthy`. |
| Frontend health | `HEALTHCHECK` polls nginx `/healthz` (does not depend on the backend). |
| Restart | All three services use `restart: unless-stopped`, so they survive crashes and host reboots; a manually stopped container stays stopped. |
| Shutdown | `stop_grace_period` 30s for backend/db and 15s for frontend. Uvicorn drains in-flight requests on `SIGTERM`; the app's lifespan hook shuts the WebSocket manager down cleanly. PostgreSQL performs a normal shutdown on `SIGTERM`. |
| Startup failure | Missing `SECRET_KEY`/`API_TOKEN`/`POSTGRES_PASSWORD`/host config aborts `docker compose up` before any container starts. |

---

## 7. Database persistence and restart behaviour

* **Where the data lives.** The `postgres-data` named volume is mounted at
  `/var/lib/postgresql/data`. It is managed by Docker and survives
  `docker compose down`, `docker compose up`, image upgrades and host reboots.
* **What destroys it.** Only `docker compose ... down -v`, `docker volume rm`,
  or explicit host-level deletion. Treat those as destructive.
* **Restart semantics.** `restart: unless-stopped` recreates a crashed container
  against the same volume, so PostgreSQL recovers its state; the backend
  reconnects with `pool_pre_ping=True` (see `backend/database/__init__.py`).
* **Backups.** Standard PostgreSQL tooling applies. From the host:

  ```bash
  docker compose -f docker-compose.prod.yml --env-file .env.production \
    exec -T db pg_dump -U qshield qshield | gzip > qshield-$(date +%F).sql.gz
  ```

  Restore by piping the dump into `psql` in the same container.
* **Honest limitation.** The **security audit ledger and analytics are
  in-memory** (`backend/security/ledger/`, `backend/security/analytics/`); they
  are *not* persisted to PostgreSQL and are lost on backend restart. Only the
  `devices`/`identity_claims`/`ledger_entries`/`trust_records` tables are real,
  and no request path currently reads or writes them. Persisting the audit
  ledger is a follow-up task.

---

## 8. Security posture and non-claims

* The API token is injected **server-side by nginx** as `X-API-Token`. It is
  never present in the served HTML/CSS/JS (those are static files that cannot
  read the container environment). `npm run check:secrets` enforces this at build
  time, and the Vite build receives no secrets.
* The token is a **deployment-level gate, not user authentication.** Every
  visitor of the site is proxied with the same token, so it stops anonymous
  public access to the API but provides **no per-user identity, scoping or
  RBAC**. Do not present it as user authentication. Put real authentication
  (SSO/OAuth2 proxy, mTLS, VPN) in front before exposing this beyond a trusted
  network.
* Rate limiting and request-size limits are enforced **in-process** by the
  backend; they do not coordinate across replicas and are not edge-grade.
* TLS is **not** configured here. Terminate TLS in front of the frontend
  (or add certificates to nginx) before any non-local exposure.
* **No source bind mounts** in production; images are immutable and run
  non-root (backend uid 10001).

---

## 9. Verification status

Docker is **not installed in the environment where these files were authored**,
so the image builds and the running stack could *not* be executed here. What was
verified instead:

* The nginx template was rendered with the same `envsubst` filter the nginx
  image uses, and nginx's own variables (`$http_upgrade`, `$connection_upgrade`,
  `$http_host`, …) were confirmed to survive.
* The production backend was started against a **real PostgreSQL 16 server**
  (`postgresql+psycopg://…`, `ENVIRONMENT=production`) and `init_db()` was
  observed to create all four tables.
* `uv run ruff check .`, `uv run pytest`, `npm run typecheck`, `npm run build`
  and `npm run check:secrets` all pass (see the task report).

Exact commands to run later on a machine with Docker:

```bash
docker compose -f docker-compose.prod.yml config      # validate the file
scripts/build-prod-images.sh local                    # build both images
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
curl -fsS http://127.0.0.1:8080/api/v1/health
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml down
```
