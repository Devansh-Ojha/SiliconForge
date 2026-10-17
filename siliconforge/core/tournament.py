"""
SiliconForge Tournament & Tree Search Orchestrator.
Allows exploration of multiple hardware micro-architectural variants in parallel,
ranking them by correctness, timing, and area.
"""

from __future__ import annotations
import concurrent.futures
from typing import Callable, Dict, Any, List, Optional
from siliconforge.core.env import HardwareEnvironment
from siliconforge.core.models import SnapshotNode, PPAMetrics


class ExplorationTournament:
    """
    Manages parallel exploration branches off a baseline snapshot.
    Evaluates candidate implementations and identifies the Pareto-optimal design.
    """

    def __init__(self, base_env: HardwareEnvironment):
        self.base_env = base_env

    def run_tournament(
        self,
        variants: List[Dict[str, Any]],
        eval_cmd: List[str],
        timing_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        variants is a list of dicts:
        [
          {
            "name": "branch_1",
            "description": "2-stage pipeline",
            "modifications": { "path/to/file.v": "new content" },
            "est_wns": 0.15,
            "est_area": 1200.0
          }, ...
        ]
        """
        results = []

        for var in variants:
            name = var["name"]
            desc = var.get("description", "")
            mods = var.get("modifications", {})

            # 1. Fast CoW fork
            child_env = self.base_env.fork(branch_name=name, description=desc)

            # 2. Apply modifications
            for rel_path, code in mods.items():
                child_env.write_file(rel_path, code)

            # 3. Compile and simulate
            metrics = child_env.evaluate(eval_cmd, timing_file=timing_file)

            # 4. If synthetic timing/area provided for benchmark tests, populate
            if var.get("est_wns") is not None and metrics.wns_ns is None:
                metrics.wns_ns = var["est_wns"]
            if var.get("est_area") is not None and metrics.area_um2 is None:
                metrics.area_um2 = var["est_area"]
            child_env.dag.update_metrics(child_env.node.id, metrics)

            results.append({
                "id": child_env.node.id,
                "name": name,
                "status": child_env.node.status.value,
                "metrics": metrics.to_dict(),
                "node": child_env.node
            })

        best = self.base_env.dag.get_best_design()
        pareto = self.base_env.dag.get_pareto_frontier()

        return {
            "summary": self.base_env.dag.export_summary(),
            "best_design": best.to_dict() if best else None,
            "pareto_designs": [p.to_dict() for p in pareto],
            "runs": results
        }
