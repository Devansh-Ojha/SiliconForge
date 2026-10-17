"""
Unit tests for SiliconForge Core: Experiment DAG, CoW Snapshotting, and Telemetry.
"""

import tempfile
from pathlib import Path
from siliconforge.core.models import SnapshotNode, PPAMetrics, NodeStatus
from siliconforge.core.dag import ExperimentDAG
from siliconforge.drivers.sandbox import CoWWorkspaceDriver
from siliconforge.telemetry.parsers import VerilatorLogParser, YosysLogParser, OpenROADTimingParser


def test_dag_pareto_frontier():
    dag = ExperimentDAG()

    # Node 1: Failed sim
    n1 = SnapshotNode(name="cand1", status=NodeStatus.FAILED)
    n1.metrics = PPAMetrics(sim_passed=False, wns_ns=0.5, area_um2=100.0)
    dag.add_node(n1)

    # Node 2: Passed, negative slack (timing violation)
    n2 = SnapshotNode(name="cand2", status=NodeStatus.SUCCESS)
    n2.metrics = PPAMetrics(sim_passed=True, wns_ns=-0.2, area_um2=500.0)
    dag.add_node(n2)

    # Node 3: Passed, timing closed, moderate area
    n3 = SnapshotNode(name="cand3", status=NodeStatus.SUCCESS)
    n3.metrics = PPAMetrics(sim_passed=True, wns_ns=0.1, area_um2=800.0)
    dag.add_node(n3)

    # Node 4: Passed, timing closed, high area
    n4 = SnapshotNode(name="cand4", status=NodeStatus.SUCCESS)
    n4.metrics = PPAMetrics(sim_passed=True, wns_ns=0.15, area_um2=1500.0)
    dag.add_node(n4)

    pareto = dag.get_pareto_frontier()
    assert len(pareto) >= 1
    best = dag.get_best_design()
    assert best is not None
    assert best.id == n3.id  # Optimal balance of timing closed & least area


def test_telemetry_parsers():
    # Verilator parser test
    stdout = "CYCLES: 512\nSIM_TIME: 1.45s\nALL TESTS PASSED\n"
    v_metrics = VerilatorLogParser.parse_simulation_output(stdout, "")
    assert v_metrics.sim_passed is True
    assert v_metrics.sim_cycles == 512
    assert v_metrics.sim_time_sec == 1.45

    # Yosys parser test
    yosys_out = "Number of cells: 342\nChip area for module 'cache': 2450.75"
    y_info = YosysLogParser.parse_synthesis(yosys_out)
    assert y_info["gate_count"] == 342
    assert y_info["chip_area"] == 2450.75

    # OpenROAD parser test
    sta_out = "Worst negative slack: -0.35\nTotal negative slack: -1.24\n"
    sta_info = OpenROADTimingParser.parse_timing_report(sta_out)
    assert sta_info["wns_ns"] == -0.35
    assert sta_info["tns_ns"] == -1.24


def test_cow_storage_driver():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        source = base_dir / "src"
        source.mkdir()
        (source / "top.v").write_text("module top; endmodule")

        driver = CoWWorkspaceDriver(base_dir)
        root_path = driver.create_root(source, "root_snap")
        assert (root_path / "top.v").exists()

        child_path = driver.snapshot("root_snap", "child_snap")
        assert (child_path / "top.v").exists()

        # Mutate child
        (child_path / "top.v").write_text("module top_mutated; endmodule")
        assert (root_path / "top.v").read_text() == "module top; endmodule"
        assert (child_path / "top.v").read_text() == "module top_mutated; endmodule"


if __name__ == "__main__":
    test_dag_pareto_frontier()
    test_telemetry_parsers()
    test_cow_storage_driver()
    print("ALL UNIT TESTS PASSED SUCCESSFULLY!")
