# Quick Start: Running the Security Framework

## Prerequisites

1. Backend running:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. Frontend running (in separate terminal):
   ```bash
   cd frontend
   npm run dev
   ```

## Running the Automated Demonstration

To validate that all security modules work correctly:

```bash
# Option 1: From backend directory
python -m validation.security_demo

# Option 2: From project root
python -m backend.validation.security_demo
```

### Expected Output

The demonstration will:
1. Create 100 legitimate devices
2. Launch a Sybil attack with 20 ghost nodes
3. Run the complete security pipeline
4. Display validation results with metrics

### Example Results

```
======================================================================
  VALIDATION RESULTS
======================================================================

  DEVICE STATISTICS:
  Total legitimate devices                       100
  Accepted devices                               100
  Ghost nodes spawned                             20
  Ghost nodes detected                            20

  ATTACK DEFENSE PERFORMANCE:
  Attack success rate                          0.00%
  Defense success rate                       100.00%
  Detection accuracy                         100.00%

  DETECTION ACCURACY METRICS:
  Precision                                  100.00%
  Recall                                     100.00%
  F1 Score                                   100.00%
  Overall Accuracy                           100.00%

  PROOF-OF-PROXIMITY METRICS:
  Total verifications                            150
  Acceptance rate                             95.00%
  Avg confidence                              92.50%
  Avg propagation delay (ms)                   0.003

  TRUST ENGINE STATISTICS:
  Total devices evaluated                       120
  Average trust score                         0.725
  Accepted devices                             100
  Monitored devices                             15
  Rejected devices                               5
  Blacklisted devices                            0

  DISTRIBUTED LEDGER:
  Total entries                                1000
  Unique devices                                120
  Shards                                         8
  Avg shard size                              125.0
```

## Accessing the Dashboard

Once the backend and frontend are running:

1. **Home**: http://localhost:5173/
2. **Simulation**: http://localhost:5173/simulation
3. **Security Overview**: http://localhost:5173/security
4. **Trust Monitor**: http://localhost:5173/security/trust
5. **Attack Monitor**: http://localhost:5173/security/attacks
6. **Analytics**: http://localhost:5173/security/analytics

## Testing Individual APIs

### Check Security Status
```bash
curl http://localhost:8000/api/v1/security/status
```

### Start a Sybil Attack
```bash
curl -X POST http://localhost:8000/api/v1/security/attack/start \
  -H "Content-Type: application/json" \
  -d '{"attacker": "test-attacker", "count": 20, "intensity": 2.0}'
```

### Get Trust Scores
```bash
curl http://localhost:8000/api/v1/security/trust
```

### Export Analytics
```bash
curl http://localhost:8000/api/v1/security/analytics/export/json > analytics.json
curl http://localhost:8000/api/v1/security/analytics/export/csv > analytics.csv
```

### Get Verification Metrics
```bash
curl http://localhost:8000/api/v1/security/verification/metrics
```

## Module Status Checklist

✅ **MODULE 1: Ghost Node Engine**
- Configurable attack strengths (10, 20, 50, 100, 250 nodes)
- Realistic Sybil behavior
- Attack statistics collection
- WebSocket event broadcasting

✅ **MODULE 2: Proof-of-Proximity**
- Time-of-Flight verification algorithm
- Distance error calculation
- Confidence scoring
- Verification history
- Metrics export

✅ **MODULE 3: Lattice Cryptography**
- Simulated PQC implementation
- Key generation, signing, verification
- Interface-based design (pluggable)
- Performance metrics collection

✅ **MODULE 4: Trust Engine**
- Multi-factor trust scoring
- Proximity-based updates
- Signature-based updates
- Behavior-based updates
- History tracking

✅ **MODULE 5: Sharded Ledger**
- Hash-based shard selection
- Append-only storage
- Device queries
- Blacklist/restore functionality
- Statistics export

✅ **MODULE 6: Integration**
- Complete join request pipeline
- Packet processing pipeline
- Attack coordination
- Event broadcasting

✅ **MODULE 7: Live Dashboard**
- Trust Monitor (real-time updates)
- Attack Monitor (control + visualization)
- Verification Analytics (metrics + export)
- WebSocket integration

✅ **MODULE 8: Research Metrics**
- Detection accuracy (Precision, Recall, F1)
- Attack/defense success rates
- Verification time tracking
- JSON/CSV export

✅ **MODULE 9: Validation**
- Automated demonstration
- Complete pipeline testing
- Metrics collection and reporting
- End-to-end validation

## Integration with Digital Twin

The security framework is integrated with the Digital Twin at:

1. **Device Joins**: `DigitalTwinManager.spawn_device()` calls `SecurityOrchestrator.receive_join()`
2. **Packet Events**: Simulator's `packet_callback` → `SecurityOrchestrator.receive_packet()`
3. **WebSocket Broadcasting**: Security events → `/api/v1/ws/stream`

## Troubleshooting

### Import Errors
Ensure Python path includes backend:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
```

### WebSocket Connection Issues
Check that:
1. Backend is running on http://localhost:8000
2. WebSocket manager is initialized
3. Check browser console for connection errors

### No Events Showing on Dashboard
1. Verify WebSocket is connected (`/api/v1/ws/stream`)
2. Check that devices are being created
3. Verify security events are being emitted

## Next Steps

1. **Run automated validation**: `python -m backend.validation.security_demo`
2. **Monitor dashboard**: http://localhost:5173/security/analytics
3. **Review metrics**: Export JSON/CSV for analysis
4. **Customize parameters**: Edit intensity, ghost count, tolerance values

## Architecture Documentation

For detailed architecture information, see: [SECURITY_FRAMEWORK_IMPLEMENTATION.md](./SECURITY_FRAMEWORK_IMPLEMENTATION.md)

