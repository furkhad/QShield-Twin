"""WebSocket connection manager with an async publish queue.

The manager exposes a thread-safe ``emit_sync`` method which can be called from
simulation threads to enqueue messages for asynchronous broadcasting by the
FastAPI event loop.

Lifecycle contract:
- ``start(loop)`` is called from the application lifespan startup. It (re)creates
  the queue/consumer bound to the *current* running loop, so a later app start
  (e.g. a second ``create_app()`` in tests) does not leave events bound to a
  closed loop.
- ``shutdown()`` is called from lifespan teardown to cancel the consumer task and
  drop all connections, preventing leaked background tasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict

from starlette.websockets import WebSocket

logger = logging.getLogger("qshield.websocket")


class WebSocketManager:
    def __init__(self, max_connections: int = 50) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.max_connections = max(1, int(max_connections))
        self._queue: asyncio.Queue[str] | None = None
        self._consumer_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def has_capacity(self) -> bool:
        """Whether another client may connect under the configured limit."""
        return len(self.active_connections) < self.max_connections

    @property
    def loop_ready(self) -> bool:
        """Whether the manager currently has a live loop to enqueue onto."""

        return (
            self._loop is not None
            and not self._loop.is_closed()
            and self._queue is not None
        )

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Bind to ``loop`` and start the background consumer.

        Safe to call multiple times: an existing consumer bound to a live loop is
        left untouched, while a stale (closed) loop is replaced.
        """

        if self.loop_ready and self._loop is loop:
            return
        if self.loop_ready:
            logger.debug("WebSocketManager already bound to a live loop; reusing it")
            return

        self._loop = loop
        self._queue = asyncio.Queue()
        self._consumer_task = loop.create_task(self._consumer())
        logger.info("WebSocketManager consumer started")

    # Backwards-compatible alias (older code called set_event_loop).
    set_event_loop = start

    async def shutdown(self) -> None:
        """Cancel the consumer task and close all connections."""

        task = self._consumer_task
        self._consumer_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - shutdown path
                pass

        self.active_connections.clear()
        self._queue = None
        self._loop = None

    async def _consumer(self) -> None:
        assert self._queue is not None
        try:
            while True:
                msg = await self._queue.get()
                try:
                    await self._broadcast(msg)
                except Exception:
                    logger.exception("Error broadcasting message")
        except asyncio.CancelledError:
            logger.info("WebSocketManager consumer cancelled")
            raise

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
        # Send to all active connections, dropping any that fail.
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(message)
            except Exception:
                logger.exception("Failed broadcasting to %s", client_id)
                self.active_connections.pop(client_id, None)

    # Thread-safe emit used by simulator threads (non-async) to enqueue messages.
    def emit_sync(self, message_obj: object) -> None:
        if not self.loop_ready:
            # Manager not ready yet; drop the message rather than raising.
            logger.debug("Emit called before event loop attached; dropping message")
            return
        try:
            msg = json.dumps(message_obj, default=str)
        except Exception:
            msg = str(message_obj)
        # schedule put_nowait on the event loop thread
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, msg)
        except RuntimeError:
            # Loop closed between the readiness check and the scheduling call.
            logger.debug("Event loop closed during emit; dropping message")


# Global manager instance used by the application
manager = WebSocketManager()
