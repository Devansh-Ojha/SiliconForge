"""
SiliconForge Hardware Environment Interface.
High-level SDK for AI agents to interact with, modify, snapshot, and evaluate RTL.
"""

from __future__ import annotations
import difflib
from pathlib import Path
from typing import Dict, Any, List, Optional
from siliconforge.core.models import SnapshotNode, PPAMetrics, NodeStatus
from siliconforge.core.dag import ExperimentDAG
from siliconforge.drivers.sandbox import CoWWorkspaceDriver, ExecutionSandbox, ExecutionResult
from siliconforge.telemetry.parsers import VerilatorLogParser, OpenROADTimingParser


class HardwareEnvironment:
    """
    An isolated, reproducible hardware development environment instance.
    Represents a specific snapshot in the experiment DAG.
    """

    def __init__(
        self,
        node: SnapshotNode,
        dag: ExperimentDAG,
        driver: CoWWorkspaceDriver
    ):
        self.node = node
        self.dag = dag
        self.driver = driver
        self.workspace_path = Path(node.storage_path)
        self.sandbox = ExecutionSandbox(self.workspace_path)

    @classmethod
    def initialize(
        cls,
        source_repo: Path,
        storage_base: Path,
        name: str = "baseline"
    ) -> HardwareEnvironment:
        driver = CoWWorkspaceDriver(storage_base)
        root_node = SnapshotNode(name=name, description="Root baseline environment")
        dest_path = driver.create_root(source_repo, root_node.id)
        root_node.storage_path = str(dest_path)

        dag = ExperimentDAG(root_node)
        return cls(root_node, dag, driver)

    def fork(self, branch_name: str, description: str = "") -> HardwareEnvironment:
        """
        Creates a sub-second copy-on-write fork of this environment.
        """
        child_node = SnapshotNode(
            parent_id=self.node.id,
            name=branch_name,
            description=description
        )
        child_path = self.driver.snapshot(self.node.id, child_node.id)
        child_node.storage_path = str(child_path)

        self.dag.add_node(child_node)
        return HardwareEnvironment(child_node, self.dag, self.driver)

    def read_file(self, relative_path: str) -> str:
        target = self.workspace_path / relative_path
        return target.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        target = self.workspace_path / relative_path
        old_content = target.read_text(encoding="utf-8") if target.exists() else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        # Compute unified diff
        diff = "\n".join(
            difflib.unified_diff(
                old_content.splitlines(),
                content.splitlines(),
                fromfile=f"a/{relative_path}",
                tofile=f"b/{relative_path}",
                lineterm=""
            )
        )
        self.node.diff_from_parent = diff

    def run_command(self, cmd: List[str], timeout: int = 120) -> ExecutionResult:
        return self.sandbox.run_command(cmd, timeout=timeout)

    def evaluate(self, sim_cmd: List[str], timing_file: Optional[str] = None) -> PPAMetrics:
        """
        Runs the simulation testbench, parses telemetry, and extracts PPA metrics.
        """
        self.dag.mark_status(self.node.id, NodeStatus.RUNNING)
        res = self.sandbox.run_command(sim_cmd)

        metrics = VerilatorLogParser.parse_simulation_output(res.stdout, res.stderr)
        if not res.success:
            metrics.sim_passed = False

        if timing_file:
            tf = self.workspace_path / timing_file
            if tf.exists():
                t_metrics = OpenROADTimingParser.parse_timing_report(tf.read_text())
                metrics.wns_ns = t_metrics.get("wns_ns")
                metrics.tns_ns = t_metrics.get("tns_ns")

        self.node.metrics = metrics
        self.node.status = NodeStatus.SUCCESS if metrics.sim_passed else NodeStatus.FAILED
        self.dag.update_metrics(self.node.id, metrics)
        return metrics

    def rollback(self) -> HardwareEnvironment:
        """
        Rolls back to the parent snapshot.
        """
        if not self.node.parent_id:
            raise ValueError("Root node cannot be rolled back.")
        self.dag.mark_status(self.node.id, NodeStatus.ROLLED_BACK)
        parent_node = self.dag.get_node(self.node.parent_id)
        if not parent_node:
            raise ValueError(f"Parent {self.node.parent_id} not found in DAG.")
        return HardwareEnvironment(parent_node, self.dag, self.driver)
