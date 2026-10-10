"""Security-related REST APIs for the Quantum-Resilient Sybil Defense Framework.

Exposes complete security orchestrator functionality:
- Attack control (start/stop)
- Trust management
- Ledger queries
- Verification metrics
- Analytics and research data export
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query

from backend.digital_twin.manager import DigitalTwinManager
from backend.simulation.environment import SimConfig
from backend.app.schemas.response import StandardResponse

router = APIRouter(prefix="/security", tags=["security"])

# Manager instance for security operations
_manager = DigitalTwinManager(config=SimConfig())


# ============================================================================
# ATTACK CONTROL
# ============================================================================


@router.post("/attack/start", response_model=StandardResponse)
def attack_start(payload: dict = Body(...)):
    """Start a Sybil attack campaign with configurable ghost nodes."""
    attacker = payload.get("attacker", "attacker-1")
    count = int(payload.get("count", 10))
    intensity = float(payload.get("intensity", 1.0))
    duration = float(payload.get("duration", 60.0))
    try:
        result = _manager.security.start_attack(
            attacker_id=attacker, count=count, intensity=intensity, duration=duration
        )
        return StandardResponse(status="ok", message="Attack started", data=result)
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to start attack", errors={"detail": str(exc)}
        )


@router.post("/attack/stop", response_model=StandardResponse)
def attack_stop(payload: dict = Body(...)):
    """Stop an active Sybil attack campaign."""
    attacker = payload.get("attacker", "attacker-1")
    try:
        result = _manager.security.stop_attack(attacker)
        return StandardResponse(status="ok", message="Attack stopped", data=result)
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to stop attack", errors={"detail": str(exc)}
        )


@router.get("/attacks", response_model=StandardResponse)
def list_attacks():
    """List all active and completed attack campaigns."""
    try:
        attacks = _manager.security.ghost.all_attack_stats()
        data = {
            attacker_id: {
                "ghost_count": stats.ghost_count,
                "intensity": stats.intensity,
                "duration": stats.duration,
                "total_packets": stats.total_packets,
                "detected_count": stats.detected_count,
                "detection_rate": stats.detection_rate,
                "success_rate": stats.success_rate,
                "status": "active" if stats.end_time is None else "completed",
            }
            for attacker_id, stats in attacks.items()
        }
        return StandardResponse(status="ok", message="Attack list", data=data)
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to list attacks", errors={"detail": str(exc)}
        )


# ============================================================================
# SECURITY STATUS
# ============================================================================


@router.get("/status", response_model=StandardResponse)
def security_status():
    """Get comprehensive security framework status."""
    try:
        st = _manager.status()
        return StandardResponse(status="ok", message="Security status", data=st)
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to get status", errors={"detail": str(exc)}
        )


@router.get("/access-control/overview", response_model=StandardResponse)
def access_control_overview():
    """Get the SecureAccess network overview for the building simulation."""
    try:
        state = _manager.status()
        return StandardResponse(
            status="ok",
            message="Access-control overview",
            data={
                "overview": state.get("overview", {}),
                "zones": state.get("access_control", {}).get("zones", []),
                "simulation": state.get("simulation", {}),
                "security": state.get("security", {}),
            },
        )
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to get overview", errors={"detail": str(exc)})


@router.get("/access-control/devices", response_model=StandardResponse)
def access_control_devices():
    """Return access-control devices with security state."""
    try:
        state = _manager.status()
        devices = state.get("devices", [])
        return StandardResponse(status="ok", message="Access-control devices", data={"devices": devices, "count": len(devices)})
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to get devices", errors={"detail": str(exc)})


@router.get("/access-control/events", response_model=StandardResponse)
def access_control_events(limit: int = Query(50, ge=1, le=200)):
    """Return the latest access-control security events."""
    try:
        events = _manager.security.status().get("recent_events", []) if _manager.security else []
        return StandardResponse(status="ok", message="Security events", data={"events": list(events)[-limit:], "count": min(len(events), limit)})
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to get events", errors={"detail": str(exc)})


@router.get("/access-control/devices/{device_id}", response_model=StandardResponse)
def access_control_device_detail(device_id: str):
    """Return detailed access-control state for a single device."""
    try:
        state = _manager.status()
        device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id), None)
        trust = _manager.security.trust.get_trust(device_id) if _manager.security else None
        ledger_entries = _manager.security.ledger.query_device(device_id) if _manager.security else []
        verification = _manager.security.proximity.get_verification_history(device_id) if _manager.security else []
        return StandardResponse(
            status="ok",
            message="Access-control device detail",
            data={
                "device": device,
                "trust": None if trust is None else {
                    "device_id": trust.device_id,
                    "score": trust.score,
                    "decision": trust.decision,
                    "risk_level": trust.risk_level,
                    "update_count": trust.update_count,
                    "reasons": trust.reasons,
                },
                "ledger": [entry.__dict__ for entry in ledger_entries],
                "verification": [item.__dict__ for item in verification],
            },
        )
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to get device detail", errors={"detail": str(exc)})


@router.post("/demo/access-control", response_model=StandardResponse)
def access_control_demo(payload: dict = Body(default={})): 
    """Run the SecureAccess access-control simulation with legitimate and ghost devices."""
    try:
        legitimate_count = int(payload.get("legitimate_count", 100))
        ghost_count = int(payload.get("ghost_count", 20))
        result = _manager.run_access_control_demo(legitimate_count=legitimate_count, ghost_count=ghost_count)
        return StandardResponse(status="ok", message="Access-control demo completed", data=result)
    except Exception as exc:
        return StandardResponse(status="error", message="Failed to run access-control demo", errors={"detail": str(exc)})


# ============================================================================
# TRUST MANAGEMENT
# ============================================================================


@router.get("/trust", response_model=StandardResponse)
def get_trust(device_id: str | None = None):
    """Get trust scores for device(s)."""
    try:
        if device_id:
            rec = _manager.security.trust.get_trust(device_id)
            if rec:
                return StandardResponse(
                    status="ok",
                    message="Trust record",
                    data={
                        "device_id": rec.device_id,
                        "score": rec.score,
                        "decision": rec.decision,
                        "risk_level": rec.risk_level,
                        "update_count": rec.update_count,
                    },
                )
            else:
                return StandardResponse(
                    status="ok", message="No trust record", data={"device_id": device_id}
                )
        else:
            # Return all trust scores
            all_scores = {}
            for device_id, rec in _manager.security.trust.get_all_trust_scores().items():
                all_scores[device_id] = {
                    "score": rec.score,
                    "decision": rec.decision,
                    "risk_level": rec.risk_level,
                }
            return StandardResponse(
                status="ok", message="All trust scores", data={"scores": all_scores}
            )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to get trust", errors={"detail": str(exc)}
        )


@router.get("/trust/high-risk", response_model=StandardResponse)
def get_high_risk_devices(threshold: float = Query(0.4)):
    """Get devices below trust threshold (high risk)."""
    try:
        devices = _manager.security.trust.get_high_risk_devices(threshold)
        return StandardResponse(
            status="ok",
            message="High risk devices",
            data={"devices": devices, "count": len(devices), "threshold": threshold},
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get high risk devices",
            errors={"detail": str(exc)},
        )


@router.get("/trust/by-decision/{decision}", response_model=StandardResponse)
def get_devices_by_decision(decision: str):
    """Get devices with specific security decision."""
    try:
        devices = _manager.security.trust.get_devices_by_decision(decision)
        return StandardResponse(
            status="ok",
            message=f"Devices with decision: {decision}",
            data={"devices": devices, "count": len(devices)},
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get devices",
            errors={"detail": str(exc)},
        )


# ============================================================================
# LEDGER MANAGEMENT
# ============================================================================


@router.get("/ledger", response_model=StandardResponse)
def get_ledger():
    """Get ledger statistics."""
    try:
        stats = _manager.security.ledger.stats()
        return StandardResponse(status="ok", message="Ledger stats", data=stats)
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to get ledger", errors={"detail": str(exc)}
        )


@router.get("/ledger/device/{device_id}", response_model=StandardResponse)
def get_ledger_device(device_id: str):
    """Get ledger entries for a specific device."""
    try:
        entries = _manager.security.ledger.query_device(device_id)
        device_status = _manager.security.ledger.get_device_status(device_id)
        return StandardResponse(
            status="ok",
            message="Ledger entries",
            data={
                "device_status": device_status,
                "entries": [
                    {
                        "timestamp": e.timestamp,
                        "accepted": e.accepted,
                        "reason": e.reason,
                        "evidence": e.evidence,
                    }
                    for e in entries
                ],
                "count": len(entries),
            },
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get ledger entries",
            errors={"detail": str(exc)},
        )


@router.get("/ledger/shard/{shard_id}", response_model=StandardResponse)
def get_shard_stats(shard_id: int):
    """Get statistics for a specific ledger shard."""
    try:
        stats = _manager.security.ledger.shard_stats(shard_id)
        return StandardResponse(
            status="ok", message="Shard statistics", data=stats
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get shard stats",
            errors={"detail": str(exc)},
        )


@router.post("/ledger/blacklist", response_model=StandardResponse)
def post_blacklist(payload: dict = Body(...)):
    """Blacklist a device (mark as untrusted)."""
    device_id = payload.get("device_id")
    reason = payload.get("reason", "manual")
    try:
        entry = _manager.security.ledger.blacklist(device_id, reason)
        return StandardResponse(
            status="ok", message="Blacklisted", data={"entry": entry.__dict__}
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to blacklist", errors={"detail": str(exc)}
        )


@router.post("/ledger/restore", response_model=StandardResponse)
def post_restore(payload: dict = Body(...)):
    """Restore a blacklisted device."""
    device_id = payload.get("device_id")
    try:
        entry = _manager.security.ledger.restore(device_id)
        return StandardResponse(
            status="ok", message="Restored", data={"entry": entry.__dict__}
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to restore", errors={"detail": str(exc)}
        )


@router.get("/ledger/export/csv", response_model=StandardResponse)
def export_ledger_csv():
    """Export ledger entries as CSV."""
    try:
        csv_content = _manager.security.ledger.export_csv()
        return StandardResponse(
            status="ok", message="Ledger CSV export", data={"csv": csv_content}
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to export CSV", errors={"detail": str(exc)}
        )


# ============================================================================
# VERIFICATION METRICS
# ============================================================================


@router.get("/verification/metrics", response_model=StandardResponse)
def verification_metrics():
    """Get proximity verification metrics."""
    try:
        metrics = _manager.security.proximity.get_metrics()
        return StandardResponse(
            status="ok", message="Verification metrics", data=metrics
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get verification metrics",
            errors={"detail": str(exc)},
        )


@router.get("/verification/device/{device_id}", response_model=StandardResponse)
def verification_history(device_id: str):
    """Get verification history for a device."""
    try:
        history = _manager.security.proximity.get_verification_history(device_id)
        return StandardResponse(
            status="ok",
            message="Verification history",
            data={
                "device_id": device_id,
                "verifications": [
                    {
                        "timestamp": v.timestamp,
                        "decision": v.decision,
                        "confidence": v.confidence,
                        "distance_error": v.distance_error,
                    }
                    for v in history
                ],
                "count": len(history),
            },
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to get verification history",
            errors={"detail": str(exc)},
        )


# ============================================================================
# ANALYTICS & RESEARCH METRICS
# ============================================================================


@router.get("/analytics", response_model=StandardResponse)
def security_analytics():
    """Get comprehensive analytics and research metrics."""
    try:
        metrics = _manager.security.analytics.metrics()
        return StandardResponse(
            status="ok", message="Analytics", data=metrics
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to get analytics", errors={"detail": str(exc)}
        )


@router.get("/analytics/export/json", response_model=StandardResponse)
def analytics_export_json():
    """Export all analytics as JSON."""
    try:
        json_content = _manager.security.analytics.export_json()
        return StandardResponse(
            status="ok", message="Analytics JSON export", data={"json": json_content}
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to export JSON",
            errors={"detail": str(exc)},
        )


@router.get("/analytics/export/csv", response_model=StandardResponse)
def analytics_export_csv():
    """Export detection results as CSV."""
    try:
        csv_content = _manager.security.analytics.export_csv()
        return StandardResponse(
            status="ok", message="Analytics CSV export", data={"csv": csv_content}
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to export CSV", errors={"detail": str(exc)}
        )


# ============================================================================
# GHOST NODE MANAGEMENT
# ============================================================================


@router.get("/ghosts", response_model=StandardResponse)
def list_ghosts():
    """List all ghost nodes."""
    try:
        ghosts = _manager.security.ghost.list_ghosts()
        data = {
            ghost.device_id: {
                "name": ghost.name,
                "attacker": ghost.attacker_id,
                "position": (ghost.x, ghost.y),
                "active": ghost.active,
                "packets_sent": ghost.packets_sent,
                "detected_at": ghost.detected_at,
            }
            for ghost in ghosts
        }
        return StandardResponse(
            status="ok", message="Ghost nodes list", data={"ghosts": data}
        )
    except Exception as exc:
        return StandardResponse(
            status="error", message="Failed to list ghosts", errors={"detail": str(exc)}
        )


@router.get("/ghosts/{attacker_id}", response_model=StandardResponse)
def list_ghosts_by_attacker(attacker_id: str):
    """List ghost nodes for specific attacker."""
    try:
        ghosts = _manager.security.ghost.list_ghosts_by_attacker(attacker_id)
        data = [
            {
                "device_id": ghost.device_id,
                "name": ghost.name,
                "position": (ghost.x, ghost.y),
                "packets_sent": ghost.packets_sent,
            }
            for ghost in ghosts
        ]
        return StandardResponse(
            status="ok",
            message=f"Ghosts for attacker {attacker_id}",
            data={"ghosts": data, "count": len(data)},
        )
    except Exception as exc:
        return StandardResponse(
            status="error",
            message="Failed to list ghosts",
            errors={"detail": str(exc)},
        )
