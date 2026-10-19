"""
Tests for AutonomousHardwareAgent and rollback recovery.
"""

import tempfile
from pathlib import Path
from siliconforge.core.env import HardwareEnvironment
from siliconforge.agent.hardware_agent import AutonomousHardwareAgent
from siliconforge.core.models import PPAMetrics


def test_autonomous_agent_rollback_loop():
    example_dir = Path(__file__).resolve().parent.parent / "examples" / "01_riscv_cache_optimization"

    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_base = Path(tmp_dir)
        base_env = HardwareEnvironment.initialize(
            source_repo=example_dir,
            storage_base=storage_base,
            name="agent_test_base"
        )

        agent = AutonomousHardwareAgent(base_env, max_iterations=3)

        def mock_policy(iteration: int, code: str, metrics: PPAMetrics):
            if iteration == 1:
                # Deliberately broken edit -> should trigger auto-rollback
                return {
                    "description": "Insert broken hit signal",
                    "code": code.replace("resp_hit <= 1'b1;", "resp_hit <= 1'b0;"),
                    "est_wns": -0.5,
                    "est_area": 900.0
                }
            elif iteration == 2:
                # Valid optimization -> should be kept
                return {
                    "description": "Valid pipelining refactor",
                    "code": code,
                    "est_wns": 0.25,
                    "est_area": 1100.0
                }
            return None

        best_node = agent.optimize_rtl(sim_cmd=["make", "run"], policy_fn=mock_policy)

        assert len(agent.history) == 2
        assert agent.history[0].decision == "ROLLBACK"
        assert agent.history[1].decision == "KEEP"
        assert best_node.metrics.wns_ns == 0.25
        print("AutonomousHardwareAgent rollback loop test passed!")


if __name__ == "__main__":
    test_autonomous_agent_rollback_loop()
