from backend.security.orchestrator import SecurityOrchestrator


def test_receive_join_detects_ghost_like_device():
    orchestrator = SecurityOrchestrator()

    result = orchestrator.receive_join(
        {
            "device_id": "ghost-123",
            "name": "ghost-123",
            "x": 1.0,
            "y": 2.0,
            "device_type": "ghost",
        }
    )

    assert result["ghost_detected"] is True
    assert result["decision"] in {"reject", "blacklist"}
