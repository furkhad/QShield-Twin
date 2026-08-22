# QShield Twin

Quantum-Resilient Sybil Defense for IoT Devices: A Physics-Based Decentralized Framework

QShield Twin is a research-grade digital twin platform for simulating decentralized IoT networks and evaluating quantum-resilient Sybil defenses. The platform provides a modular, extensible codebase with a FastAPI backend and a React + TypeScript frontend.

## Features
- Digital twin simulation for decentralized IoT networks
- Configurable Sybil attack engine (ghost nodes)
- Simulated proof-of-proximity
- Pluggable post-quantum cryptography abstraction
- Sharded trust ledger and evidence tracking
- Interactive dashboard, visualization, and analytics

## Quickstart
Prerequisites:
- Python 3.12
- Node.js 18+
- npm or yarn
- Docker (optional)

Backend (development):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows PowerShell
pip install -r ../requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (development):
```bash
cd frontend
npm install
npm run dev
```

Run tests:
```bash
pytest -q
```

Docker (compose):
```bash
docker-compose up --build
```

For full documentation, see the `docs/` directory.
