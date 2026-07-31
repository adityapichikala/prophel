"""
Topology Building Module for Karnataka SPDB Fault Localization System.

Explicitly implements Case A (Known Topology) and Case B (60% Missing Topology via Geometric Nearest-Parent MST).

Case B Approach Details:
We construct a Minimum Spanning Tree (MST)-like structure rooted at the DT's GPS location.
For each unattached pole, its parent is selected as the nearest pole already attached to the tree
that is strictly closer to the DT than itself (greedy nearest-parent-towards-root).
A distance threshold cap (default 250 meters) is enforced; if no connected candidate is within range,
the pole is treated as a separate spur branch root directly connected to the DT.

Known Failure Modes of Geometric Inference:
1. Parallel Spurs: Two LT lines running parallel along opposite sides of a narrow street can be mis-connected across the street rather than along their true physical wiring path.
2. Dense Clusters: In dense urban clusters with multi-directional branching, geometric distance alone can mistake a secondary branch root for a continuation of the main feeder run.
"""

import math
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

@dataclass
class PoleData:
    pole_id: str
    lat: float
    lon: float
    seq_on_line: Optional[int] = None
    parent_pole_id: Optional[str] = None
    dt_id: str = ""
    feeder_id: str = ""

@dataclass
class TopologyEdge:
    parent_id: Optional[str]  # None if root pole connected to DT
    child_id: str
    is_inferred: bool
    confidence: float  # 0.95 for recorded, 0.65 for inferred
    distance_meters: float

@dataclass
class Tree:
    dt_id: str
    topology_known: bool
    root_poles: List[str] = field(default_factory=list)  # Poles connected directly to DT
    parent_map: Dict[str, Optional[str]] = field(default_factory=dict)  # pole_id -> parent_pole_id
    children_map: Dict[str, List[str]] = field(default_factory=dict)  # pole_id -> list of child_pole_ids
    edges: Dict[str, TopologyEdge] = field(default_factory=dict)  # child_id -> TopologyEdge
    confidence_score: float = 0.95

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in meters between two lat/lon coordinates."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

def build_topology(
    dt_id: str,
    dt_lat: float,
    dt_lon: float,
    poles: List[PoleData],
    max_span_distance_m: float = 250.0
) -> Tree:
    """
    Pure, testable logic to construct a tree topology for a Distribution Transformer (DT).
    
    Case A (Recorded Topology): If seq_on_line and parent_pole_id are present, use directly.
    Case B (Missing 60% Topology): Greedy nearest-parent-towards-root MST algorithm based on GPS.
    """
    if not poles:
        return Tree(dt_id=dt_id, topology_known=True, confidence_score=1.0)

    # Check if explicit recorded topology exists (Case A)
    has_recorded = any(p.parent_pole_id is not None or p.seq_on_line is not None for p in poles)

    if has_recorded:
        return _build_recorded_topology(dt_id, dt_lat, dt_lon, poles)
    else:
        return _build_inferred_topology(dt_id, dt_lat, dt_lon, poles, max_span_distance_m)

def _build_recorded_topology(
    dt_id: str,
    dt_lat: float,
    dt_lon: float,
    poles: List[PoleData]
) -> Tree:
    tree = Tree(dt_id=dt_id, topology_known=True, confidence_score=0.95)
    pole_dict = {p.pole_id: p for p in poles}

    for p in poles:
        tree.children_map[p.pole_id] = []

    for p in poles:
        parent = p.parent_pole_id
        if not parent or parent not in pole_dict:
            tree.root_poles.append(p.pole_id)
            tree.parent_map[p.pole_id] = None
            dist = haversine(dt_lat, dt_lon, p.lat, p.lon)
            tree.edges[p.pole_id] = TopologyEdge(
                parent_id=None,
                child_id=p.pole_id,
                is_inferred=False,
                confidence=0.95,
                distance_meters=dist
            )
        else:
            tree.parent_map[p.pole_id] = parent
            tree.children_map[parent].append(p.pole_id)
            parent_p = pole_dict[parent]
            dist = haversine(parent_p.lat, parent_p.lon, p.lat, p.lon)
            tree.edges[p.pole_id] = TopologyEdge(
                parent_id=parent,
                child_id=p.pole_id,
                is_inferred=False,
                confidence=0.95,
                distance_meters=dist
            )

    return tree

def _build_inferred_topology(
    dt_id: str,
    dt_lat: float,
    dt_lon: float,
    poles: List[PoleData],
    max_span_distance_m: float
) -> Tree:
    tree = Tree(dt_id=dt_id, topology_known=False, confidence_score=0.65)
    pole_dict = {p.pole_id: p for p in poles}

    for p in poles:
        tree.children_map[p.pole_id] = []

    # Calculate distance of each pole from DT
    dt_dists = {p.pole_id: haversine(dt_lat, dt_lon, p.lat, p.lon) for p in poles}
    
    # Sort poles ascending by distance to DT (closest first)
    sorted_poles = sorted(poles, key=lambda p: dt_dists[p.pole_id])

    connected: Set[str] = set()

    for p in sorted_poles:
        pid = p.pole_id
        p_dist_dt = dt_dists[pid]

        if not connected:
            # First closest pole connected to DT as root
            tree.root_poles.append(pid)
            tree.parent_map[pid] = None
            connected.add(pid)
            tree.edges[pid] = TopologyEdge(
                parent_id=None,
                child_id=pid,
                is_inferred=True,
                confidence=0.65,
                distance_meters=p_dist_dt
            )
            continue

        # Find nearest parent among already connected poles that is closer to DT than p
        best_parent = None
        best_dist = float('inf')

        for conn_id in connected:
            if dt_dists[conn_id] < p_dist_dt:
                conn_p = pole_dict[conn_id]
                d = haversine(conn_p.lat, conn_p.lon, p.lat, p.lon)
                if d < best_dist and d <= max_span_distance_m:
                    best_dist = d
                    best_parent = conn_id

        if best_parent:
            tree.parent_map[pid] = best_parent
            tree.children_map[best_parent].append(pid)
            connected.add(pid)
            tree.edges[pid] = TopologyEdge(
                parent_id=best_parent,
                child_id=pid,
                is_inferred=True,
                confidence=0.65,
                distance_meters=best_dist
            )
        else:
            # Distance cap exceeded or no closer parent found; treat as separate root branch from DT
            tree.root_poles.append(pid)
            tree.parent_map[pid] = None
            connected.add(pid)
            tree.edges[pid] = TopologyEdge(
                parent_id=None,
                child_id=pid,
                is_inferred=True,
                confidence=0.60,
                distance_meters=p_dist_dt
            )

    return tree
