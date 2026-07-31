import math
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

@dataclass
class PoleNode:
    pole_id: str
    lat: float
    lon: float
    feeder_id: str
    dt_id: str
    seq_on_line: Optional[int]
    parent_pole_id: Optional[str]
    pincode: str
    device_id: Optional[str]
    energized: bool = True
    last_telemetry_ts: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)

@dataclass
class FaultLocalizationResult:
    incident_id: str
    fault_type: str  # 'SPAN_FAULT', 'DT_FAULT', 'FEEDER_FAULT', 'DEAD_SENSOR'
    target_id: str  # Span (e.g., 'P-01->P-02'), DT ID, Feeder ID, or Pole ID
    substation_id: str
    feeder_id: str
    dt_id: str
    pincode: str
    lat: float
    lon: float
    affected_poles_count: int
    confidence: float
    confidence_reason: str
    topology_known: bool
    affected_pole_ids: List[str]
    root_dark_pole_id: Optional[str] = None
    upstream_live_pole_id: Optional[str] = None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns distance in meters between two lat/lon points."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class NetworkTopologyGraph:
    def __init__(self):
        self.poles: Dict[str, PoleNode] = {}
        self.dt_poles: Dict[str, List[str]] = {}
        self.feeder_dts: Dict[str, Set[str]] = {}
        self.dt_locations: Dict[str, Tuple[float, float]] = {}
        self.dt_topology_known: Dict[str, bool] = {}

    def add_dt(self, dt_id: str, feeder_id: str, lat: float, lon: float, topology_known: bool = True):
        self.dt_locations[dt_id] = (lat, lon)
        self.dt_topology_known[dt_id] = topology_known
        if feeder_id not in self.feeder_dts:
            self.feeder_dts[feeder_id] = set()
        self.feeder_dts[feeder_id].add(dt_id)
        if dt_id not in self.dt_poles:
            self.dt_poles[dt_id] = []

    def add_pole(self, pole: PoleNode):
        self.poles[pole.pole_id] = pole
        if pole.dt_id not in self.dt_poles:
            self.dt_poles[pole.dt_id] = []
        self.dt_poles[pole.dt_id].append(pole.pole_id)

    def build_dt_trees(self):
        """
        Build parent-child relationships for all DTs.
        For DTs with missing topology (topology_known=False or missing parent_pole_ids),
        construct a Prim's Minimum Spanning Tree (MST) from surveyed GPS coordinates.
        """
        for dt_id, pole_ids in self.dt_poles.items():
            dt_known = self.dt_topology_known.get(dt_id, False)
            dt_lat, dt_lon = self.dt_locations.get(dt_id, (0.0, 0.0))

            # Reset existing children
            for pid in pole_ids:
                self.poles[pid].children_ids = []

            # Check if explicit topology exists
            has_explicit = dt_known and any(self.poles[pid].parent_pole_id for pid in pole_ids)

            if has_explicit:
                # 40% case: Explicit topology available
                for pid in pole_ids:
                    p = self.poles[pid]
                    if p.parent_pole_id and p.parent_pole_id in self.poles:
                        self.poles[p.parent_pole_id].children_ids.append(pid)
            else:
                # 60% case: Inferred topology via Minimum Spanning Tree (MST)
                self._build_mst_for_dt(dt_id, pole_ids, dt_lat, dt_lon)

    def _build_mst_for_dt(self, dt_id: str, pole_ids: List[str], dt_lat: float, dt_lon: float):
        """Construct MST using Prim's algorithm rooted at DT location."""
        if not pole_ids:
            return

        unvisited = set(pole_ids)
        visited = set()

        # Connect closest pole to DT first
        first_pole_id = min(unvisited, key=lambda pid: haversine_distance(dt_lat, dt_lon, self.poles[pid].lat, self.poles[pid].lon))
        visited.add(first_pole_id)
        unvisited.remove(first_pole_id)
        self.poles[first_pole_id].parent_pole_id = None  # Root pole connected to DT

        while unvisited:
            best_dist = float('inf')
            best_parent = None
            best_child = None

            for v_id in visited:
                v_pole = self.poles[v_id]
                for u_id in unvisited:
                    u_pole = self.poles[u_id]
                    dist = haversine_distance(v_pole.lat, v_pole.lon, u_pole.lat, u_pole.lon)
                    if dist < best_dist:
                        best_dist = dist
                        best_parent = v_id
                        best_child = u_id

            if best_child and best_parent:
                self.poles[best_child].parent_pole_id = best_parent
                self.poles[best_parent].children_ids.append(best_child)
                visited.add(best_child)
                unvisited.remove(best_child)

    def localize_faults(self, dark_pole_ids: Set[str], scheduled_outage_targets: Set[str]) -> List[FaultLocalizationResult]:
        """
        Core Fault Localization Algorithm:
        1. Ignore dark poles covered by scheduled outages.
        2. Identify dead sensors (isolated dark pole whose children are energized).
        3. Check Feeder-level & DT-level complete outages.
        4. Traverses live/dark boundaries on trees to find exact span faults.
        5. Computes confidence and produces structured incidents.
        """
        results = []

        # Filter active dark poles against scheduled outages
        active_dark = set()
        for pid in dark_pole_ids:
            p = self.poles.get(pid)
            if not p:
                continue
            if p.feeder_id in scheduled_outage_targets or p.dt_id in scheduled_outage_targets:
                continue  # Scheduled outage, ignore!
            active_dark.add(pid)

        if not active_dark:
            return results

        # 1. Filter out Dead Sensors (Isolated dark pole with live children)
        real_dark = set()
        for pid in active_dark:
            pole = self.poles[pid]
            children = [self.poles[c] for c in pole.children_ids if c in self.poles]
            # If pole has children and ALL children are ENERGIZED (live), it's a dead sensor!
            if children and all(c.pole_id not in active_dark for c in children):
                results.append(FaultLocalizationResult(
                    incident_id=f"INC-SENSOR-{pid}",
                    fault_type="DEAD_SENSOR",
                    target_id=pid,
                    substation_id="SUB-01",
                    feeder_id=pole.feeder_id,
                    dt_id=pole.dt_id,
                    pincode=pole.pincode or "560078",
                    lat=pole.lat,
                    lon=pole.lon,
                    affected_poles_count=1,
                    confidence=0.99,
                    confidence_reason="Isolated dark sensor with live downstream children. Dead sensor, not outage.",
                    topology_known=self.dt_topology_known.get(pole.dt_id, False),
                    affected_pole_ids=[pid],
                    root_dark_pole_id=pid
                ))
            else:
                real_dark.add(pid)

        if not real_dark:
            return results

        # 2. Check Feeder Level Outages
        dt_dark_counts: Dict[str, Tuple[int, int]] = {}  # dt_id -> (dark_count, total_count)
        for dt_id, pole_ids in self.dt_poles.items():
            total = len(pole_ids)
            dark = sum(1 for pid in pole_ids if pid in real_dark)
            dt_dark_counts[dt_id] = (dark, total)

        # Check feeder outage
        handled_dts = set()
        for feeder_id, dts in self.feeder_dts.items():
            if not dts:
                continue
            total_dark_dts = sum(1 for dt in dts if dt_dark_counts.get(dt, (0, 1))[0] > 0 and dt_dark_counts.get(dt, (0, 1))[0] >= 0.8 * dt_dark_counts.get(dt, (0, 1))[1])
            if total_dark_dts >= 0.8 * len(dts) and len(dts) > 1:
                # Feeder level outage!
                affected_poles = [pid for dt in dts for pid in self.dt_poles.get(dt, []) if pid in real_dark]
                sample_pole = self.poles[affected_poles[0]] if affected_poles else None
                results.append(FaultLocalizationResult(
                    incident_id=f"INC-FEEDER-{feeder_id}",
                    fault_type="FEEDER_FAULT",
                    target_id=feeder_id,
                    substation_id="SUB-01",
                    feeder_id=feeder_id,
                    dt_id="ALL",
                    pincode=sample_pole.pincode if sample_pole else "560078",
                    lat=sample_pole.lat if sample_pole else 12.9716,
                    lon=sample_pole.lon if sample_pole else 77.5946,
                    affected_poles_count=len(affected_poles),
                    confidence=0.95,
                    confidence_reason="Over 80% of distribution transformers on feeder went dark simultaneously.",
                    topology_known=True,
                    affected_pole_ids=affected_poles
                ))
                handled_dts.update(dts)

        # 3. Check DT Level & Span Level Outages per DT
        for dt_id, pole_ids in self.dt_poles.items():
            if dt_id in handled_dts:
                continue

            dark_in_dt = [pid for pid in pole_ids if pid in real_dark]
            if not dark_in_dt:
                continue

            dt_known = self.dt_topology_known.get(dt_id, False)
            dt_lat, dt_lon = self.dt_locations.get(dt_id, (12.9716, 77.5946))
            total_poles = len(pole_ids)

            # Check if whole DT is down (>90% dark)
            if len(dark_in_dt) >= 0.9 * total_poles and total_poles >= 3:
                sample_pole = self.poles[dark_in_dt[0]]
                results.append(FaultLocalizationResult(
                    incident_id=f"INC-DT-{dt_id}",
                    fault_type="DT_FAULT",
                    target_id=dt_id,
                    substation_id="SUB-01",
                    feeder_id=sample_pole.feeder_id,
                    dt_id=dt_id,
                    pincode=sample_pole.pincode or "560078",
                    lat=dt_lat,
                    lon=dt_lon,
                    affected_poles_count=len(dark_in_dt),
                    confidence=0.92 if dt_known else 0.85,
                    confidence_reason=f"Entire distribution transformer {dt_id} is dark. Blown HT fuse or DT failure.",
                    topology_known=dt_known,
                    affected_pole_ids=dark_in_dt
                ))
                continue

            # Find Root Boundary Dark Poles (dark poles whose parent is live or None)
            boundary_roots = []
            for pid in dark_in_dt:
                parent_id = self.poles[pid].parent_pole_id
                if not parent_id or parent_id not in real_dark:
                    boundary_roots.append(pid)

            for root_id in boundary_roots:
                root_pole = self.poles[root_id]
                upstream_live = root_pole.parent_pole_id

                # Collect all downstream dark poles in this subtree
                subtree_dark = self._get_subtree_poles(root_id, real_dark)

                # Determine span identifier
                if upstream_live:
                    target_span = f"{upstream_live} -> {root_id}"
                else:
                    target_span = f"DT_{dt_id} -> {root_id}"

                # Calculate confidence
                if dt_known:
                    conf = 0.92
                    reason = f"Exact span fault identified on verified line topology between {upstream_live or 'DT'} and {root_id}."
                else:
                    conf = 0.65
                    reason = f"Span fault inferred on geometric MST tree between {upstream_live or 'DT'} and {root_id} (Missing digitized topology)."

                results.append(FaultLocalizationResult(
                    incident_id=f"INC-SPAN-{root_id}",
                    fault_type="SPAN_FAULT",
                    target_id=target_span,
                    substation_id="SUB-01",
                    feeder_id=root_pole.feeder_id,
                    dt_id=dt_id,
                    pincode=root_pole.pincode or "560078",
                    lat=(root_pole.lat + (self.poles[upstream_live].lat if upstream_live in self.poles else dt_lat)) / 2.0,
                    lon=(root_pole.lon + (self.poles[upstream_live].lon if upstream_live in self.poles else dt_lon)) / 2.0,
                    affected_poles_count=len(subtree_dark),
                    confidence=conf,
                    confidence_reason=reason,
                    topology_known=dt_known,
                    affected_pole_ids=list(subtree_dark),
                    root_dark_pole_id=root_id,
                    upstream_live_pole_id=upstream_live
                ))

        return results

    def _get_subtree_poles(self, root_id: str, dark_set: Set[str]) -> Set[str]:
        """Traverse downstream tree to collect all dark poles."""
        collected = {root_id}
        stack = [root_id]
        while stack:
            curr = stack.pop()
            curr_pole = self.poles[curr]
            for child in curr_pole.children_ids:
                if child in dark_set and child not in collected:
                    collected.add(child)
                    stack.append(child)
        return collected
