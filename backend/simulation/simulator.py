"""SimPy-based simulator orchestrating the Digital Twin.

This module provides a Simulator class that controls the SimPy environment
and runs device actor processes. It exposes start/pause/reset interfaces
used by the API controllers.
"""

from __future__ import annotations

import random
import threading
import threading as _threading
import time
from collections import deque
from dataclasses import asdict
from typing import Dict, Optional

import simpy

from backend.simulation.communication import CommunicationEngine
from backend.simulation.device import SimDevice
from backend.simulation.network import NetworkGraph


class Simulator:
    def __init__(self, seed: Optional[int] = None, broadcaster: Optional[callable] = None) -> None:
        self.env = simpy.Environment()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially
        self.running = False
        self.devices: Dict[str, SimDevice] = {}
        self.network = NetworkGraph()
        self.comm = CommunicationEngine()
        # broadcaster is a synchronous callable that accepts a serializable
        # object. In the running application it will typically be
        # `backend.app.websocket.manager.manager.emit_sync` which enqueues
        # messages for the async event loop.
        self.broadcaster = broadcaster
        self.packet_callback: Optional[callable] = None
        # history buffer for snapshots and packet events (lightweight)
        self.history: deque = deque(maxlen=1000)
        self._replay_thread: Optional[_threading.Thread] = None
        self._replay_stop = False
        if seed is not None:
            import random

            random.seed(seed)

    def add_device(self, device: SimDevice) -> None:
        self.devices[device.device_id] = device
        self.network.add_device(device)

    def remove_device(self, device_id: str) -> None:
        self.devices.pop(device_id, None)
        self.network.remove_device(device_id)

    def _device_process(self, device: SimDevice):
        """A simple device actor that periodically broadcasts presence."""
        while True:
            # Broadcast presence
            device.status = "active"
            # Recompute network edges on each broadcast
            self.network.update_edges()
            # Sleep for a simulated second
            yield self.env.timeout(1)

    def _publisher_process(self):
        """Periodically publish snapshots via the configured broadcaster."""
        while True:
            # produce a lightweight snapshot for efficiency
            snapshot = {
                "time": self.env.now,
                "devices": [
                    {
                        "device_id": d.device_id,
                        "name": d.name,
                        "x": d.x,
                        "y": d.y,
                        "latency_ms": d.latency_ms,
                        "packets_sent": d.packets_sent,
                        "packets_received": d.packets_received,
                        "battery": d.battery,
                        "trust_score": d.trust_score,
                    }
                    for d in self.devices.values()
                ],
                "links": list(self.network.graph.edges()),
            }
            if self.broadcaster:
                try:
                    self.broadcaster(snapshot)
                except Exception:
                    # Broadcaster should be robust; swallow errors to avoid stopping sim
                    pass

            # Occasionally generate a packet event between random connected nodes
            try:
                edges = list(self.network.graph.edges())
                if edges and random.random() < 0.4:
                    src, dst = random.choice(edges)
                    src_dev = self.devices.get(src)
                    dst_dev = self.devices.get(dst)
                    if src_dev and dst_dev:
                        distance = src_dev.distance_to(dst_dev)
                        latency = self.comm.latency_fn(distance)
                        pkt_event = {"type": "packet", "time": self.env.now, "src": src, "dst": dst, "latency_ms": latency}
                        if self.broadcaster:
                            try:
                                self.broadcaster(pkt_event)
                            except Exception:
                                pass
                        # also notify packet callback (synchronous)
                        if self.packet_callback:
                            try:
                                self.packet_callback(pkt_event)
                            except Exception:
                                pass
                        # record to history
                        try:
                            self.history.append({"kind": "packet", "event": pkt_event})
                        except Exception:
                            pass
            except Exception:
                # don't let publisher crash due to transient network issues
                pass
            # record snapshot to history buffer
            try:
                self.history.append({"kind": "snapshot", "snapshot": snapshot})
            except Exception:
                pass
            yield self.env.timeout(1)

    # History/replay APIs
    def get_history(self, limit: int = 200):
        return list(self.history)[-limit:]

    def replay_history(self, speed: float = 1.0, start: int | None = None, end: int | None = None):
        """Replay history by broadcasting stored snapshot/packet events at given speed (1.0 = realtime).

        Runs in a background thread; call stop_replay() to cancel.
        """
        if self._replay_thread and self._replay_thread.is_alive():
            # already replaying
            return

        hist = list(self.history)
        if start is None:
            start = 0
        if end is None:
            end = len(hist)

        def runner():
            self._replay_stop = False
            for item in hist[start:end]:
                if self._replay_stop:
                    break
                if item.get("kind") == "snapshot":
                    # broadcast snapshot
                    try:
                        self.broadcaster(item["snapshot"])
                    except Exception:
                        pass
                    time.sleep(1.0 / max(0.01, speed))
                elif item.get("kind") == "packet":
                    try:
                        self.broadcaster(item["event"])
                    except Exception:
                        pass
                    time.sleep(0.05)

        self._replay_thread = _threading.Thread(target=runner, daemon=True)
        self._replay_thread.start()

    def stop_replay(self):
        self._replay_stop = True
        if self._replay_thread and self._replay_thread.is_alive():
            self._replay_thread.join(timeout=1.0)

    def start(self, runtime: float = 10.0) -> None:
        if self.running:
            return

        def runner():
            # Register processes for existing devices
            for d in list(self.devices.values()):
                self.env.process(self._device_process(d))
            # register publisher
            self.env.process(self._publisher_process())
            self.running = True
            self._stop_requested = False
            # run in small time slices so we can pause/resume/step
            try:
                while not self._stop_requested:
                    # respect pause
                    self._pause_event.wait()
                    # advance simulation by 1 time unit
                    target = self.env.now + 1
                    self.env.run(until=target)
            finally:
                self.running = False

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()

    def reset(self) -> None:
        # Stop current thread by recreating environment and data structures
        self._stop_requested = True
        # wake from pause so thread can exit
        self._pause_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.env = simpy.Environment()
        self.devices.clear()
        self.network = NetworkGraph()
        self.comm = CommunicationEngine()
        self.running = False

    def status(self) -> Dict[str, object]:
        return {
            "running": self.running,
            "device_count": len(self.devices),
            "time": self.env.now,
        }

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def step(self, steps: int = 1) -> None:
        # advance the simulation by `steps` time units
        for _ in range(steps):
            self.env.run(until=self.env.now + 1)

    def snapshot(self):
        return [asdict(d) for d in self.devices.values()]
