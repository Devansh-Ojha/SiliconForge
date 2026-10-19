"""
Tests for Waveform Extractor, Web Dashboard Server, and Benchmark 01.
"""

import tempfile
import urllib.request
import json
from pathlib import Path

from siliconforge.telemetry.waveform import WaveformSliceExtractor
from siliconforge.ui.server import DashboardServer
from siliconforge.core.dag import ExperimentDAG
from siliconforge.core.models import SnapshotNode, PPAMetrics, NodeStatus


def test_waveform_slice_extractor():
    vcd_content = """$date today $end
$version Model $end
$timescale 1ns $end
$scope module top $end
$var wire 1 ! clk $end
$var wire 1 " resp_hit $end
$var wire 1 # error $end
$upscope $end
$enddefinitions $end
#0
0!
0"
0#
#10
1!
#20
0!
1"
#30
1!
1#
#40
0!
"""
    with tempfile.NamedTemporaryFile("w+", suffix=".vcd", delete=False) as f:
        f.write(vcd_content)
        vcd_path = Path(f.name)

    try:
        extractor = WaveformSliceExtractor(vcd_path)
        window = extractor.extract_anomaly_window(failure_time=30, clock_period=10)
        assert window["failure_time"] == 30
        assert "ascii_diagram" in window
        assert "error" in window["signals"]
        assert window["signals"]["error"][30] == "1"
    finally:
        if vcd_path.exists():
            vcd_path.unlink()


def test_dashboard_server():
    dag = ExperimentDAG()
    root = SnapshotNode(name="root_base", status=NodeStatus.SUCCESS)
    root.metrics = PPAMetrics(sim_passed=True, wns_ns=0.1, area_um2=1200.0)
    dag.add_node(root)
    dag.root_id = root.id

    server = DashboardServer(dag, port=8899)
    server.start(blocking=False)

    try:
        # Test HTTP API endpoint
        req = urllib.request.urlopen("http://localhost:8899/api/dag", timeout=3)
        assert req.status == 200
        data = json.loads(req.read().decode())
        assert data["total_nodes"] == 1
        assert data["root_id"] == root.id

        # Test HTML index
        req_html = urllib.request.urlopen("http://localhost:8899/", timeout=3)
        assert req_html.status == 200
        html = req_html.read().decode()
        assert "SiliconForge" in html
    finally:
        server.stop()


if __name__ == "__main__":
    test_waveform_slice_extractor()
    test_dashboard_server()
    print("ALL WAVEFORM, DASHBOARD & BENCHMARK TESTS PASSED!")
