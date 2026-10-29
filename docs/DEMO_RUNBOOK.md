# QShield-Twin Live Demo Runbook

Target date: **2026-10-30**. This runbook is written for the verified local
single-machine demo: FastAPI backend, Vite/React frontend, SQLite ledger, and a
browser on `127.0.0.1`.

The scripted scenario is **10 legitimate access-control devices + 2 ghost/Sybil
identities**. It is a simulation, not a production access-control system.

---

## 1. What the demo proves

1. The backend and frontend start from a known state.
2. Twelve identities are processed through the security pipeline: 12 joins and
   12 packets.
3. All 10 legitimate devices are connected and `monitor`; both ghost identities
   are `reject` with trust `0.0`.
4. A real WebSocket event stream is delivered to the browser.
5. The 8-shard ledger records 24 entries and verifies its hash chains.
6. The same SQLite database survives a backend restart with the ledger intact.
7. A post-restart append is durable and verifies.
8. JSON/CSV exports are downloadable from the UI and API.

It does **not** prove production security, real-world detection accuracy, hardware
ToF ranging, or blockchain-style consensus.

---

## 2. Preflight (before the audience arrives)

From `/home/learn/Projects/QShield-Twin`:

```bash
uv run pytest -q
uv run ruff check .
cd frontend
npm run typecheck
npm run build
npm run check:secrets
cd ..
```

Expected on the verified tree:

- `pytest`: **102 tests, exit code 0** (17 test files; no failures). Note that
  `pyproject.toml` already sets `-q`, so passing `-q` again suppresses pytest's
  final summary line; the run is still successful if the exit code is 0.
- `ruff`: `All checks passed!`
- `tsc --noEmit`: no errors.
- `vite build`: succeeds.
- `check:secrets`: `OK: no API token present in the production bundle.`

Tests use the isolated temp DB set by `tests/conftest.py`; they must not be
pointed at the demo or repository database.

---

## 3. Prepare the demo database

Use a database outside the repository:

```bash
export DEMO_DB="$HOME/.local/share/qshield-twin/demo-2026-10-30.db"
mkdir -p "$(dirname "$DEMO_DB")"

# Archive any previous demo state. Do not reuse a database with unknown history
# if you need the exact counts below.
if [ -f "$DEMO_DB" ]; then
  stamp=$(date +%Y%m%d-%H%M%S)
  mv "$DEMO_DB" "$DEMO_DB.$stamp.bak"
  if [ -f "$DEMO_DB-wal" ]; then mv "$DEMO_DB-wal" "$DEMO_DB-wal.$stamp.bak"; fi
  if [ -f "$DEMO_DB-shm" ]; then mv "$DEMO_DB-shm" "$DEMO_DB-shm.$stamp.bak"; fi
fi
```

A fresh run creates the database on first backend start. The ledger accumulates
across scenario reruns and restarts; device and trust state do **not**.

The rehearsal database from the verified 10 + 2 + restart run (25 ledger entries)
is archived next to it as `demo-2026-10-30.db.verified-25-entries-*`. It is
evidence only; do not start the demo from it if you want the zero-entry baseline
and the exact counts in this runbook.

---

## 4. Start the services

### Terminal 1 — backend

```bash
cd /home/learn/Projects/QShield-Twin
export DEMO_DB="$HOME/.local/share/qshield-twin/demo-2026-10-30.db"
export DATABASE_URL="sqlite:///$DEMO_DB"
DATABASE_URL="$DATABASE_URL" \
ENVIRONMENT=development \
LOG_LEVEL=INFO \
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

`sqlite:///$DEMO_DB` expands to `sqlite:////home/...` because `DEMO_DB` is
absolute. Startup must not print a traceback. A persistence failure is fatal by
design (`LedgerPersistenceError`); it does not silently fall back to an in-memory
ledger.

### Terminal 2 — frontend

```bash
cd /home/learn/Projects/QShield-Twin/frontend
npm run dev -- --host 127.0.0.1
```

The Vite dev server proxies `/api` and the WebSocket to `localhost:8000`.

Open: <http://127.0.0.1:5173/dashboard>

### Baseline checks

```bash
curl -sS http://127.0.0.1:8000/api/v1/health
curl -sS http://127.0.0.1:8000/api/v1/version
curl -sS http://127.0.0.1:8000/api/v1/security/ledger
```

Expected:

- health: `"status":"ok"`, `"status":"healthy"`.
- version: application version `0.2.0`.
- ledger on a fresh DB: `"total_entries": 0`.

The dashboard should say **WebSocket Connected**. If it says
**WebSocket Reconnecting**, check Terminal 1 and refresh the page.

---

## 5. Run the 10 + 2 scenario

### Option A — UI (recommended)

On `/dashboard`, click **Run Ghost/Sybil Simulation**. The button posts:

```json
{"legitimate_count": 10, "ghost_count": 2}
```

Wait for `Access-control demo completed. Live data refreshed from backend state.`
Expected dashboard values:

| Field | Expected |
|---|---|
| Total devices | 12 |
| Active / trusted / monitoring | 10 / 10 / 10 |
| Rejected | 2 |
| Blacklisted | 0 |
| Average trust | 50% |
| Acceptance rate | 83% (10 of 12 total identities) |
| Legitimate acceptance | 100% (10 of 10 legitimate devices) |
| Ghost detections | 2 |
| Ledger entries | 24 |
| Detection precision / recall / F1 | 100% / 100% / 100% |

The device table should show:

- 10 rows (`door-controller-001` … `sensor-001`): authentication `Verified`,
  proximity `Accept`, trust `74–75/100`, decision `Monitor`.
- `access-node-0001` and `access-node-0002`: authentication `Failed`, proximity
  `Reject`, trust `0/100`, decision `Reject`.

### Option B — API

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/security/demo/access-control \
  -H 'Content-Type: application/json' \
  -d '{"legitimate_count": 10, "ghost_count": 2}'
```

Verified response summary:

```text
scenario            access_control_attack
device_count        10
ghost_count         2
processed_joins     12
processed_packets   12
ghost_nodes         2
attack              ghost_count=2, detected_count=2, detection_rate=1.0
ledger              total_entries=24, accepted=10, rejected=14, unique_devices=12
trust               average_trust≈0.4992, monitored=10, blacklisted=2
```

### WebSocket proof

With the dashboard open, the **WebSocket Connected** badge and the
**Security Events** panel are the simplest live proof. To inspect the raw stream,
open a third terminal **before** running the scenario:

```bash
cd /home/learn/Projects/QShield-Twin
uv run python - <<'PY'
import asyncio, json
import websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8000/api/v1/ws/stream") as ws:
        await ws.send("demo-ready")
        print(await ws.recv())  # ack:demo-ready
        seen = 0
        while seen < 5:
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            payload = message.get("payload", {})
            if message.get("type") == "security_event" and payload.get("event_type"):
                print(payload["event_type"], payload.get("device_id"),
                      payload.get("decision"), payload.get("trust_score"))
                seen += 1

asyncio.run(main())
PY
```

Then click the UI button. Expect `device_join` / `packet_verified` lines with live
decisions and trust values. A ghost join emitted during the verified run was:

```text
device_join access-node-0001 reject 0.0
security_status=rejected
detection_score=0.95
detection_reasons=["proximity deviation 135.912m", "high packet rate 45.82/s"]
```

---

## 6. Inspect trust, analytics, and ledger

### Trust Monitor

Open <http://127.0.0.1:5173/security/trust>.

Expected: **Accepted 0, Monitored 10, Rejected 0, Blacklisted 2**, 12 rows.

This screen displays the **trust engine's** decision. The access-control device
table displays the **final access decision**. For the two ghost identities the
final decision is `reject` (trust < 0.4), while the trust engine labels the same
records `blacklist`. They are the same two devices; this is not a third pair.

### Verification and analytics

Open <http://127.0.0.1:5173/security/analytics>.

Expected: total verifications `24`, acceptance rate `91.7%`, average confidence
`88.3%`, precision/recall/F1/accuracy `100.0%`, ghosts spawned `2`, ghosts
detected `2`, defense success rate `100%`.

Confusion matrix from the verified run:

```text
TP=4  FP=0  TN=20  FN=0
```

These 100% figures are synthetic-scenario results, not a real-world claim.

### Ledger integrity

Open <http://127.0.0.1:5173/security> for the raw status JSON, or use the API:

```bash
curl -sS http://127.0.0.1:8000/api/v1/security/ledger
curl -sS http://127.0.0.1:8000/api/v1/security/ledger/integrity
```

Expected before restart:

```text
ledger:    total_entries=24, accepted_entries=10, rejected_entries=14,
           blacklisted_count=0, unique_devices=12
integrity: valid=true, checked=24, broken=[]
```

The `/security/attacks` and `/security/ghosts` pages stay empty after this
scenario. The access-control scenario scores ghost identities through the
detector; it does not launch a legacy ghost-engine campaign. Use
`/dashboard`, `/security/trust`, and `/security/analytics` for this demo.

---

## 7. Exports

### UI

- `/security/analytics` → **Export as JSON** / **Export as CSV**.
- `/export` → **JSON Export** and **CSV Export** cards; after a successful click
  they show `✓ Exported`, and the history panel lists the export.

Verified behavior: JSON export card downloads a `.json` file; CSV card downloads
a `.csv` file; both update the history panel. There were no browser console
errors on the verified pages.

### API

```bash
curl -sS http://127.0.0.1:8000/api/v1/security/ledger/export/csv \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["csv"])' \
  > /tmp/qshield-ledger.csv

curl -sS http://127.0.0.1:8000/api/v1/security/analytics/export/json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["json"])' \
  > /tmp/qshield-analytics.json

curl -sS http://127.0.0.1:8000/api/v1/security/analytics/export/csv \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["csv"])' \
  > /tmp/qshield-analytics.csv
```

Expected ledger CSV: header + 24 rows = **25 lines**. After the post-restart
append described below: **26 lines** (25 entries).

The `/export` **PDF Report** button actually downloads a **Markdown** file
(`.md`), despite its label. The **Advanced Export Options** cards are visual
placeholders and do not export anything.

---

## 8. Restart durability verification

This is the key durability proof. It applies to the **ledger**, not live device
state.

1. In Terminal 1 press `Ctrl+C`. Wait for `Application shutdown complete`.
2. Confirm the port is closed:

   ```bash
   curl -sS -m 2 http://127.0.0.1:8000/api/v1/health || echo "backend stopped"
   ```

3. Start the backend again with the **same** `DATABASE_URL` command from
   Section 4.
4. Verify restoration:

   ```bash
   curl -sS http://127.0.0.1:8000/api/v1/security/ledger
   curl -sS http://127.0.0.1:8000/api/v1/security/ledger/integrity
   ```

   Expected: `total_entries=24`; `valid=true, checked=24, broken=[]`.

5. Append after restart:

   ```bash
   curl -sS -X POST http://127.0.0.1:8000/api/v1/security/ledger/blacklist \
     -H 'Content-Type: application/json' \
     -d '{"device_id":"demo-post-restart","reason":"post-restart-verification"}'
   curl -sS http://127.0.0.1:8000/api/v1/security/ledger
   curl -sS http://127.0.0.1:8000/api/v1/security/ledger/integrity
   ```

   Expected: `total_entries=25`, `blacklisted_count=1`,
   `valid=true, checked=25, broken=[]`.

6. Optional second restart: stop and start again; expected `total_entries=25`
   and `valid=true, checked=25`. This was verified.

**Important:** after a restart the dashboard shows `0 devices`, empty trust
analytics, and the restored ledger. Device, trust, and analytics state are
in-memory and are rebuilt by rerunning the scenario. Rerunning 10 + 2 appends
another 24 ledger entries; it does not replace the existing ones.

---

## 9. Shutdown

- Terminal 1: `Ctrl+C`.
- Terminal 2: `Ctrl+C`.
- Confirm:

  ```bash
  ss -ltnp | grep -E ':8000|:5173' || echo "ports free"
  ```

Do not delete the demo database after a successful run; it is the restart
evidence. Use a new path or archive it if you need a clean count next time.

---

## 10. Five-minute presentation script

| Time | Action | Say / show |
|---|---|---|
| 0:00 | Show terminal preflight and clean demo DB state | "Pytest 102/102, lint clean, frontend typecheck/build/secrets clean." |
| 0:30 | Show `/api/v1/health`, `/version`, ledger `0` | "Fresh isolated demo DB, no prior ledger entries." |
| 0:45 | Open `/dashboard` | "WebSocket Connected; this is live backend state, not a mock." |
| 1:15 | Click **Run Ghost/Sybil Simulation** | "10 legitimate devices, 2 ghost identities." |
| 1:45 | Point to metric cards | "12 total; 10 monitoring; 2 rejected; 0 blacklisted; ledger 24." |
| 2:15 | Point to device table | "Legitimate: verified, proximity accepted, 74–75 trust, monitor. Ghosts: failed, proximity reject, 0 trust, reject." |
| 2:45 | Open `/security/trust` | "10 monitored; the two ghost records are labelled blacklist by the trust engine; the final access decision is reject." |
| 3:15 | Open `/security/analytics` | "24 verifications; 2 ghosts spawned and detected; 100% on this synthetic scenario only." |
| 3:30 | Show ledger API/integrity, then export CSV | "24 entries; integrity valid, 24 checked, zero broken; export is real." |
| 4:00 | Restart backend; rerun integrity | "Same DB: 24 entries restored, still valid." |
| 4:20 | Append `demo-post-restart` blacklist; integrity | "25 entries after append, still valid; append survives another restart." |
| 4:40 | Show limitations | "Simulated PQC/ToF, local tamper-evident ledger not blockchain, device state resets on restart." |
| 5:00 | Q&A | — |

---

## 11. Troubleshooting

**Port 8000 or 5173 already in use**

```bash
ss -ltnp | grep -E ':8000|:5173'
```

Stop only the process you started. Do not kill unrelated browser or system
processes.

**Backend fails to start with `LedgerPersistenceError`**

The configured SQLite file is unreadable/corrupt or contains invalid ledger rows.
Check Terminal 1. Do not bypass persistence; archive the DB and start a new one
using Section 3, or restore a known-good copy.

**Dashboard shows 0 devices after restart**

Expected. Device/trust/analytics state is in-memory. Rerun 10 + 2 if you need the
device view; the ledger will grow by 24 entries.

**Counts differ from this runbook**

The demo DB already has entries, or the scenario was run more than once. Archive
it with Section 3 and start fresh. Ledger counts accumulate; device counts reset
per scenario run.

**Trust says `blacklist` but the device table says `reject`**

Both refer to the same two ghost identities. The trust engine and the final
access decision use different labels. The ledger's `blacklisted_count` remains 0
until you explicitly call the blacklist endpoint.

**`/security/attacks` or `/security/ghosts` is empty**

Expected for this scenario. Those pages expose the legacy ghost engine, which is
not used by the access-control scenario. Use the access-control pages.

**WebSocket says Reconnecting**

Check Terminal 1, confirm `curl http://127.0.0.1:8000/api/v1/health`, then refresh
the browser. The Vite proxy forwards `/api` including WebSocket upgrades.

**`jq: command not found`**

Use the Python one-liners in this runbook. `jq` is not required.

**Presentation page**

`/presentation` is a staged ~27-second animation that runs a 100-device / 20-ghost
scenario and appends many ledger entries. Do not use it in the 5-minute script
unless rehearsed. It is not the source of the 10 + 2 results above.

---

## 12. Known limitations and honesty notes

- **Simulation only.** PQC is a simulated lattice interface; ToF/proximity is
  software-simulated; synthetic ground truth drives the metrics.
- **Ledger scope.** Local single-process, 8-shard SHA-256 hash chain. It detects
  naive tampering but is not a blockchain, has no consensus/replication, and can
  be forged by an attacker who can rewrite the whole chain.
- **Restart scope.** Only the ledger is durable. Devices, trust records, recent
  events, and analytics are reset in memory.
- **Trust vs access label.** See Section 6.
- **Ghost engine pages.** The scenario's ghost identities are scored by the
  detector; the legacy ghost engine lists stay empty.
- **Exports.** PDF card produces Markdown; advanced export cards are placeholders.
- **API exposure.** With no `API_TOKEN`, the local API is open. Bind to
  `127.0.0.1` and do not expose it to an untrusted network.
- **Performance.** Detection/verification timing values are in-process simulation
  measurements, not hardware benchmarks.
- **Synthetic 100% metrics.** The verified 10 + 2 scenario reports precision,
  recall, F1, and accuracy of 1.0. Do not present that as real-world accuracy.
