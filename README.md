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

The configured attack scenario can also introduce suspicious identities such as:

- `door-controller-001-copy`
- `door-controller-001-clone`
- `fake-reader-01`
- other ghost-style identities

## Technical Honesty

- The PQC layer is a simulated lattice-based cryptography interface, not production Kyber or Dilithium.
- The proximity layer is software-simulated ToF verification, not hardware-grade ranging.
- The ledger is a local 8-shard hash-based audit ledger, not a blockchain or distributed consensus network.
- The demo metrics are simulation results from a configured scenario, not real-world deployment accuracy.

## Repository Layout

- `backend/` FastAPI backend, digital twin, security pipeline, ledger, analytics, validation.
- `frontend/` React + TypeScript + Vite dashboard.
- `tests/` backend and security tests.
- `backend/validation/security_demo.py` scripted SecureAccess demonstration.

## Run Backend

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

## Run the Security Demonstration

```bash
python -m backend.validation.security_demo
```

The demo runs a configured access-control scenario with legitimate devices and simulated ghost identities, then prints the resulting metrics and writes a JSON report to `logs/secureaccess_demo_results.json`.

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
- `GET /api/v1/security/trust`
- `GET /api/v1/security/analytics`
- `GET /api/v1/security/verification/metrics`
- `GET /api/v1/ws/stream`

Other existing simulation and network endpoints remain available for the digital twin.

## Testing

```bash
pytest -q
```

The test suite includes the original backend checks plus access-control coverage for legitimate joins, clone detection, the demo scenario, and API endpoints.

## Limitations

- This is a prototype and simulation environment.
- The cryptography, proximity, and ledger layers are intentionally modeled abstractions.
- Detection and trust scores are scenario-dependent and should not be interpreted as deployment-grade security guarantees.
- Real hardware integration would require device APIs, secure provisioning, and operational validation beyond this codebase.
