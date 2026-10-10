"""Network representation using NetworkX to maintain connectivity and topology."""

from __future__ import annotations

from typing import Dict, List

import networkx as nx
import random
import math
from math import ceil

from backend.simulation.device import SimDevice


class NetworkGraph:
    """Wraps a NetworkX graph and provides neighbor discovery utilities."""

    def __init__(self) -> None:
        self.graph = nx.Graph()

    def add_device(self, device: SimDevice) -> None:
        self.graph.add_node(device.device_id, device=device)

    def remove_device(self, device_id: str) -> None:
        if device_id in self.graph:
            self.graph.remove_node(device_id)

    def update_edges(self) -> None:
        """Recompute edges based on communication radius of devices."""
        self.graph.remove_edges_from(list(self.graph.edges()))
        nodes = list(self.graph.nodes(data=True))
        for i, (id1, data1) in enumerate(nodes):
            d1: SimDevice = data1["device"]
            for id2, data2 in nodes[i + 1 :]:
                d2: SimDevice = data2["device"]
                if d1.distance_to(d2) <= max(d1.comms_radius, d2.comms_radius):
                    self.graph.add_edge(d1.device_id, d2.device_id)

    def neighbors(self, device_id: str) -> List[str]:
        return list(self.graph.neighbors(device_id)) if device_id in self.graph else []

    def degree_statistics(self) -> Dict[str, float]:
        degrees = [d for _, d in self.graph.degree()]
        if not degrees:
            return {"min": 0, "max": 0, "avg": 0}
        return {"min": min(degrees), "max": max(degrees), "avg": sum(degrees) / len(degrees)}

    def populate_topology(self, devices: List[SimDevice], topology: str = "random", **kwargs) -> None:
        """Assign positions to devices according to the requested topology.

        Supported topologies: 'random', 'grid', 'cluster'. This method mutates
        `devices` in-place (setting `x` and `y`) and updates the internal graph.
        """
        if topology == "random":
            self._populate_random(devices, kwargs.get("area_size", 1000))
        elif topology == "grid":
            self._populate_grid(devices, kwargs.get("rows"), kwargs.get("cols"), kwargs.get("spacing", 50))
        elif topology == "cluster":
            self._populate_cluster(devices, kwargs.get("centers", 3), kwargs.get("spread", 20))
        elif topology == "mesh":
            self._populate_mesh(devices)
        elif topology == "star":
            self._populate_star(devices, kwargs.get("hub_index", 0))
        else:
            raise ValueError(f"Unknown topology: {topology}")

        # Ensure graph contains all devices and recompute edges
        for d in devices:
            if d.device_id not in self.graph:
                self.add_device(d)
        self.update_edges()

    def _populate_random(self, devices: List[SimDevice], area_size: float) -> None:
        for d in devices:
            d.x = random.uniform(0, area_size)
            d.y = random.uniform(0, area_size)

    def _populate_grid(self, devices: List[SimDevice], rows: int | None, cols: int | None, spacing: float = 50.0) -> None:
        n = len(devices)
        if rows is None and cols is None:
            cols = int(ceil(n ** 0.5))
            rows = int(ceil(n / cols))
        elif rows is None:
            rows = int(ceil(n / cols))
        elif cols is None:
            cols = int(ceil(n / rows))

        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx >= n:
                    break
                d = devices[idx]
                d.x = c * spacing
                d.y = r * spacing
                idx += 1

    def _populate_cluster(self, devices: List[SimDevice], centers: int = 3, spread: float = 20.0) -> None:
        n = len(devices)
        # choose cluster centers
        center_points = [(random.uniform(0, 500), random.uniform(0, 500)) for _ in range(centers)]
        for i, d in enumerate(devices):
            cx, cy = center_points[i % centers]
            d.x = random.gauss(cx, spread)
            d.y = random.gauss(cy, spread)

    def _populate_mesh(self, devices: List[SimDevice]) -> None:
        """Place devices randomly but ensure high connectivity by increasing comms_radius."""
        # place randomly then bump comms_radius to connect many nodes
        self._populate_random(devices, area_size=500)
        for d in devices:
            d.comms_radius = max(d.comms_radius, 250)

    def _populate_star(self, devices: List[SimDevice], hub_index: int = 0) -> None:
        """Place devices in a star topology around the chosen hub index."""
        n = len(devices)
        if n == 0:
            return
        hub = devices[hub_index % n]
        hub.x = 250
        hub.y = 250
        radius = 150
        for i, d in enumerate(devices):
            if d is hub:
                continue
            angle = 2 * math.pi * (i / max(1, n - 1))
            d.x = hub.x + radius * math.cos(angle)
            d.y = hub.y + radius * math.sin(angle)
            # ensure spokes have sufficient radius
            d.comms_radius = max(d.comms_radius, radius + 10)
