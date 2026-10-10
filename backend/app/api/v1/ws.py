"""WebSocket endpoints for streaming simulation events to clients.

Access control
--------------
* When ``API_TOKEN`` is configured the handshake must present it (as a ``token``
  query parameter or an ``Authorization``/``X-API-Token`` header); otherwise the
  connection is rejected with close code ``1008`` (policy violation).
* The number of concurrent connections is bounded by ``MAX_WS_CONNECTIONS``;
  excess connections are rejected with close code ``1013`` (try again later).
* Oversized client frames are rejected to avoid unbounded memory use.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.security import websocket_token_ok
from backend.app.websocket.manager import manager as ws_manager
from backend.settings import get_settings

logger = logging.getLogger("qshield.websocket")

router = APIRouter()

# Reject oversized client frames to avoid unbounded memory use.
_MAX_CLIENT_MESSAGE_BYTES = 4096


@router.websocket("/ws/stream")
async def stream_events(websocket: WebSocket) -> None:
    """Stream security/simulation events to a connected dashboard client.

    The connection is receive-oriented: the server pushes events and the client
    may send small acknowledgements/pings. Authorization and connection limits are
    enforced before the connection is accepted, and the connection is always
    cleaned up, even on unexpected errors.
    """

    settings = getattr(websocket.app.state, "settings", None) or get_settings()

    if not websocket_token_ok(websocket, settings):
        logger.warning("Rejected unauthenticated WebSocket connection")
        await websocket.close(code=1008)  # policy violation
        return

    if not ws_manager.has_capacity():
        logger.warning("Rejected WebSocket connection: connection limit reached")
        await websocket.close(code=1013)  # try again later
        return

    client_id = str(uuid.uuid4())
    await ws_manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if len(data.encode("utf-8", errors="ignore")) > _MAX_CLIENT_MESSAGE_BYTES:
                await websocket.close(code=1009)  # 1009 = message too big
                break
            await ws_manager.send_personal_message(client_id, f"ack:{data}")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unexpected WebSocket error for client %s", client_id)
    finally:
        ws_manager.disconnect(client_id)
