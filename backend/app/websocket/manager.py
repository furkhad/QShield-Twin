"""WebSocket connection manager with an async publish queue.

The manager exposes a thread-safe `emit_sync` method which can be called
from simulation threads to enqueue messages for async broadcasting by the
FastAPI event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict

from starlette.websockets import WebSocket

logger = logging.getLogger("qshield.websocket")


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self._queue: asyncio.Queue[str] | None = None
        self._consumer_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Attach the FastAPI event loop and start the background consumer."""
        if self._loop is not None:
            return
        self._loop = loop
        self._queue = asyncio.Queue()
        self._consumer_task = asyncio.create_task(self._consumer())
        logger.info("WebSocketManager consumer started")

    async def _consumer(self) -> None:
        assert self._queue is not None
        while True:
            msg = await self._queue.get()
            try:
                await self._broadcast(msg)
            except Exception:
                logger.exception("Error broadcasting message")

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket connected: %s", client_id)

    def disconnect(self, client_id: str) -> None:
        ws = self.active_connections.pop(client_id, None)
        if ws:
            logger.info("WebSocket disconnected: %s", client_id)

    async def send_personal_message(self, client_id: str, message: str) -> None:
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(message)

    async def _broadcast(self, message: str) -> None:
        # send to all active connections
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(message)
            except Exception:
                logger.exception("Failed broadcasting to %s", client_id)

    # Thread-safe emit used by simulator threads (non-async) to enqueue messages
    def emit_sync(self, message_obj: object) -> None:
        if self._loop is None or self._queue is None:
            # manager not ready yet; drop the message
            logger.debug("Emit called before event loop attached; dropping message")
            return
        try:
            msg = json.dumps(message_obj, default=str)
        except Exception:
            msg = str(message_obj)
        # schedule put_nowait on the event loop thread
        self._loop.call_soon_threadsafe(self._queue.put_nowait, msg)


# Global manager instance used by the application
manager = WebSocketManager()
