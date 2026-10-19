"""
Tests for SynthesisEngine and HypervisorManager.
"""

import tempfile
from pathlib import Path
from siliconforge.telemetry.synthesis import SynthesisEngine
from siliconforge.vmm.firecracker import HypervisorManager, VmConfig, FirecrackerDriver


def test_hypervisor_detection():
    # Should detect host fallback when /dev/kvm is not present
    backend = HypervisorManager.get_recommended_backend()
    assert backend in ("firecracker", "cow_sandbox")


def test_synthesis_script_generation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = SynthesisEngine(Path(tmp_dir))
        script = engine.generate_yosys_script("top_alu", ["alu.v", "adder.v"])
        assert "read_verilog alu.v" in script
        assert "read_verilog adder.v" in script
        assert "hierarchy -check -top top_alu" in script
        assert "write_verilog -noattr synth.v" in script


def test_synthesis_engine_fallback():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = SynthesisEngine(Path(tmp_dir))
        res = engine.run_synthesis("top_alu", ["alu.v"])
        assert "available" in res


if __name__ == "__main__":
    test_hypervisor_detection()
    test_synthesis_script_generation()
    test_synthesis_engine_fallback()
    print("ALL VMM & SYNTHESIS TESTS PASSED!")
