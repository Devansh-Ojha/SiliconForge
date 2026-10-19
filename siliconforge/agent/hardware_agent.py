"""
SiliconForge Autonomous Hardware Agent.
Connects an LLM or heuristic policy to a HardwareEnvironment.
Performs autonomous iterative edit -> simulate -> evaluate -> branch/rollback loops.
"""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from siliconforge.core.env import HardwareEnvironment
from siliconforge.core.models import SnapshotNode, PPAMetrics, NodeStatus


@dataclass
class AgentStepResult:
    iteration: int
    action_type: str
    target_file: str
    diff: str
    metrics: PPAMetrics
    decision: str  # "KEEP", "ROLLBACK", "FORK"
    explanation: str


class AutonomousHardwareAgent:
    """
    Autonomous Hardware Agent that interacts directly with the SiliconForge execution engine.
    Applies candidate RTL transformations, checks simulation validity, inspects PPA,
    and rolls back broken states.
    """

    def __init__(
        self,
        env: HardwareEnvironment,
        agent_name: str = "SiliconAgent-01",
        max_iterations: int = 5
    ):
        self.env = env
        self.agent_name = agent_name
        self.max_iterations = max_iterations
        self.history: List[AgentStepResult] = []

    def optimize_rtl(
        self,
        sim_cmd: List[str],
        policy_fn: Callable[[int, str, Optional[PPAMetrics]], Optional[Dict[str, Any]]],
        target_file: str = "riscv_cache.v"
    ) -> SnapshotNode:
        """
        Runs an autonomous loop:
          1. Reads current RTL state.
          2. Calls policy_fn to produce candidate transformation.
          3. Writes change and evaluates simulation / PPA.
          4. If simulation fails, automatically rolls back to the prior checkpoint.
          5. If simulation passes, checkpoints working state and explores further.
        """
        # Baseline evaluation
        baseline_metrics = self.env.evaluate(sim_cmd)
        print(f"[{self.agent_name}] Initial baseline evaluation: passed={baseline_metrics.sim_passed}")

        current_env = self.env
        best_env = current_env

        for i in range(1, self.max_iterations + 1):
            current_code = current_env.read_file(target_file)
            proposal = policy_fn(i, current_code, current_env.node.metrics)
            if not proposal:
                print(f"[{self.agent_name}] Convergence reached or no further modifications at iteration {i}.")
                break

            action_desc = proposal.get("description", f"Iteration {i} modification")
            new_code = proposal.get("code", current_code)

            # Fork a new isolated branch
            branch_env = current_env.fork(
                branch_name=f"{self.agent_name}_iter_{i}",
                description=action_desc
            )
            branch_env.write_file(target_file, new_code)

            # Evaluate candidate
            metrics = branch_env.evaluate(sim_cmd)
            sim_passed = metrics.sim_passed

            # Synthetic metric injection if policy supplied estimates
            if proposal.get("est_wns") is not None and metrics.wns_ns is None:
                metrics.wns_ns = proposal["est_wns"]
            if proposal.get("est_area") is not None and metrics.area_um2 is None:
                metrics.area_um2 = proposal["est_area"]
            branch_env.dag.update_metrics(branch_env.node.id, metrics)

            if not sim_passed:
                print(f"[{self.agent_name}] Iteration {i} failed simulation. Rolling back.")
                branch_env.rollback()
                decision = "ROLLBACK"
            else:
                print(f"[{self.agent_name}] Iteration {i} passed simulation. Checkpointing state.")
                decision = "KEEP"
                current_env = branch_env
                best_env = branch_env

            self.history.append(AgentStepResult(
                iteration=i,
                action_type="EDIT_RTL",
                target_file=target_file,
                diff=branch_env.node.diff_from_parent or "",
                metrics=metrics,
                decision=decision,
                explanation=action_desc
            ))

        return best_env.node
