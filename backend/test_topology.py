"""
Unit tests for build_topology function.
Tests cases:
(a) Full recorded topology (Case A)
(b) Missing topology, simple linear line (Case B)
(c) Missing topology, branching line (Case B)
(d) Documented failure mode: parallel spurs mis-connection (Case B)
"""

import pytest
from backend.topology_builder import build_topology, PoleData

def test_case_a_full_recorded_topology():
    dt_id = "D-0101"
    dt_lat, dt_lon = 12.9678, 77.5951
    poles = [
        PoleData("P-1", 12.9680, 77.5951, seq_on_line=1, parent_pole_id=None, dt_id=dt_id),
        PoleData("P-2", 12.9682, 77.5951, seq_on_line=2, parent_pole_id="P-1", dt_id=dt_id),
        PoleData("P-3", 12.9684, 77.5951, seq_on_line=3, parent_pole_id="P-2", dt_id=dt_id),
    ]

    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    assert tree.topology_known is True
    assert tree.confidence_score == 0.95
    assert tree.root_poles == ["P-1"]
    assert tree.parent_map["P-2"] == "P-1"
    assert tree.parent_map["P-3"] == "P-2"
    assert tree.edges["P-2"].is_inferred is False


def test_case_b_linear_line_inferred_topology():
    dt_id = "D-0201"
    dt_lat, dt_lon = 12.9678, 77.5951
    # 3 poles in a straight line extending north without recorded parents
    poles = [
        PoleData("P-101", 12.9680, 77.5951, dt_id=dt_id),
        PoleData("P-102", 12.9682, 77.5951, dt_id=dt_id),
        PoleData("P-103", 12.9684, 77.5951, dt_id=dt_id),
    ]

    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    assert tree.topology_known is False
    assert tree.confidence_score == 0.65
    assert tree.root_poles == ["P-101"]
    assert tree.parent_map["P-102"] == "P-101"
    assert tree.parent_map["P-103"] == "P-102"
    assert tree.edges["P-102"].is_inferred is True


def test_case_b_branching_line_inferred_topology():
    dt_id = "D-0301"
    dt_lat, dt_lon = 12.9678, 77.5951
    # Main line north, spur branching east from P-202
    poles = [
        PoleData("P-201", 12.9680, 77.5951, dt_id=dt_id),  # 22m N
        PoleData("P-202", 12.9682, 77.5951, dt_id=dt_id),  # 44m N
        PoleData("P-203", 12.9684, 77.5951, dt_id=dt_id),  # 66m N
        PoleData("P-SPUR-1", 12.96825, 77.5954, dt_id=dt_id), # Branch east of P-202
    ]

    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    assert tree.topology_known is False
    assert tree.root_poles == ["P-201"]
    assert tree.parent_map["P-202"] == "P-201"
    assert tree.parent_map["P-203"] == "P-202"
    # P-SPUR-1 should be connected to P-202 or P-201 (nearest connected pole closer to DT)
    assert tree.parent_map["P-SPUR-1"] in ["P-201", "P-202"]


def test_case_b_known_failure_mode_parallel_spurs():
    """
    DOCUMENTED FAILURE CASE:
    Two parallel LT lines running close together (e.g. 15m apart across a narrow alleyway).
    Line 1: DT -> A1 -> A2 -> A3
    Line 2: DT -> B1 -> B2 -> B3
    Because B2 is geographically very close to A2, purely greedy distance inference
    may connect B2 to A2 instead of B1, creating an artificial cross-line bridge.
    """
    dt_id = "D-0401"
    dt_lat, dt_lon = 12.9678, 77.5951
    poles = [
        # Line A (North)
        PoleData("A1", 12.9680, 77.5950, dt_id=dt_id),
        PoleData("A2", 12.9682, 77.5950, dt_id=dt_id),
        # Line B (North, 10m East)
        PoleData("B1", 12.9680, 77.5951, dt_id=dt_id),
        PoleData("B2", 12.96821, 77.59509, dt_id=dt_id), # Extremely close to A2!
    ]

    tree = build_topology(dt_id, dt_lat, dt_lon, poles)

    # Inferred tree flag must be marked false for confidence awareness
    assert tree.topology_known is False
    # All edges are flagged as inferred so UI can display lower confidence to operator
    for edge in tree.edges.values():
        assert edge.is_inferred is True
