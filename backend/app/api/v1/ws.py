"""WebSocket endpoints for streaming simulation events to clients."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.websocket.manager import manager as ws_manager

router = APIRouter()


@router.websocket("/ws/stream")
async def stream_events(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await ws_manager.connect(client_id, websocket)
    try:
        while True:
            # keep connection open; allow clients to send pings or commands
            data = await websocket.receive_text()
            # echo back for now
            await ws_manager.send_personal_message(client_id, f"ack:{data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id)
