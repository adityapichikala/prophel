"""
Synthetic Network Seed Generator.
Generates 4 Substations, 31 Feeders, 412 DTs, and ~4,000 Poles matching the exact proportions:
- ~91% poles equipped with IoT telemetry devices
- ~60% DTs missing recorded pole ordering (parent_pole_id & seq_on_line)
- Realistic Bangalore / Karnataka GPS coordinates around 12.9716 N, 77.5946 E.
"""

import random
from typing import Dict, List, Tuple
from backend.models import DtRegistry, PoleRegistry, PoleState
from backend.topology_builder import PoleData, build_topology, Tree

def generate_synthetic_network(
    num_substations: int = 4,
    num_feeders: int = 31,
    num_dts: int = 412,
    total_poles: int = 4000
) -> Tuple[List[DtRegistry], List[PoleRegistry], List[PoleState], Dict[str, Tree]]:
    random.seed(42)  # Deterministic seed for reproducible tests and demos

    dt_list: List[DtRegistry] = []
    pole_list: List[PoleRegistry] = []
    state_list: List[PoleState] = []
    trees: Dict[str, Tree] = {}

    base_lat, base_lon = 12.9716, 77.5946
    poles_per_dt = max(1, total_poles // num_dts)

    feeder_ids = [f"F-{i+1:02d}" for i in range(num_feeders)]

    for dt_idx in range(num_dts):
        dt_id = f"D-{dt_idx+1:04d}"
        feeder_id = feeder_ids[dt_idx % num_feeders]
        
        # DT Location
        dt_lat = base_lat + random.uniform(-0.05, 0.05)
        dt_lon = base_lon + random.uniform(-0.05, 0.05)
        
        # 60% missing topology rule!
        topology_known = (dt_idx % 10) >= 6  # 40% known (True), 60% missing (False)

        dt_obj = DtRegistry(
            dt_id=dt_id,
            feeder_id=feeder_id,
            lat=dt_lat,
            lon=dt_lon,
            capacity_kva=random.choice([100, 250, 500]),
            households_served=random.randint(50, 350),
            topology_known=topology_known
        )
        dt_list.append(dt_obj)

        dt_poles_data: List[PoleData] = []
        curr_lat, curr_lon = dt_lat, dt_lon

        for p_idx in range(poles_per_dt):
            pole_id = f"P-{dt_idx+1:04d}-{p_idx+1:02d}"
            device_fitted = random.random() < 0.91  # 91% coverage
            device_id = f"KSPDB-DEV-{pole_id}" if device_fitted else None

            # Radiate out from DT
            curr_lat += random.uniform(0.0001, 0.0003)
            curr_lon += random.uniform(-0.0001, 0.0002)

            seq_on_line = (p_idx + 1) if topology_known else None
            parent_pole_id = (f"P-{dt_idx+1:04d}-{p_idx:02d}") if (topology_known and p_idx > 0) else None

            pole_obj = PoleRegistry(
                pole_id=pole_id,
                lat=curr_lat,
                lon=curr_lon,
                feeder_id=feeder_id,
                dt_id=dt_id,
                seq_on_line=seq_on_line,
                parent_pole_id=parent_pole_id,
                pole_type=random.choice(["LT-9m-PCC", "LT-8m-Steel"]),
                ward=f"W-08{random.randint(1, 9)}",
                pincode="560078",
                device_id=device_id
            )
            pole_list.append(pole_obj)

            # Initial pole state (Energized)
            state_list.append(PoleState(
                pole_id=pole_id,
                device_id=device_id,
                energized=True,
                last_event_type="heartbeat",
                last_seq=1
            ))

            dt_poles_data.append(PoleData(
                pole_id=pole_id,
                lat=curr_lat,
                lon=curr_lon,
                seq_on_line=seq_on_line,
                parent_pole_id=parent_pole_id,
                dt_id=dt_id,
                feeder_id=feeder_id
            ))

        # Build Graph Tree
        tree = build_topology(dt_id, dt_lat, dt_lon, dt_poles_data)
        trees[dt_id] = tree

    return dt_list, pole_list, state_list, trees
