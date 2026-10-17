"""
SiliconForge Experiment DAG & Tree Search Manager.
Tracks checkpoints, branches, rollbacks, and Pareto frontier.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional
from siliconforge.core.models import SnapshotNode, PPAMetrics, NodeStatus


class ExperimentDAG:
    """Directed Acyclic Graph of experimental hardware states."""

    def __init__(self, root_node: Optional[SnapshotNode] = None):
        self.nodes: Dict[str, SnapshotNode] = {}
        self.root_id: Optional[str] = None
        if root_node:
            self.add_node(root_node)
            self.root_id = root_node.id

    def add_node(self, node: SnapshotNode) -> None:
        self.nodes[node.id] = node
        if node.parent_id and node.parent_id in self.nodes:
            if node.id not in self.nodes[node.parent_id].children_ids:
                self.nodes[node.parent_id].children_ids.append(node.id)

    def get_node(self, node_id: str) -> Optional[SnapshotNode]:
        return self.nodes.get(node_id)

    def mark_status(self, node_id: str, status: NodeStatus) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].status = status

    def update_metrics(self, node_id: str, metrics: PPAMetrics) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].metrics = metrics

    def get_pareto_frontier(self) -> List[SnapshotNode]:
        """
        Finds Pareto-optimal designs across valid passed simulations.
        Objectives:
          1. Maximize WNS (Worst Negative Slack, closer to >= 0 is better).
          2. Minimize Area (area_um2 or gate_count).
        """
        valid_nodes = [
            n for n in self.nodes.values()
            if n.metrics.sim_passed and n.metrics.wns_ns is not None
        ]
        if not valid_nodes:
            return []

        pareto: List[SnapshotNode] = []
        for cand in valid_nodes:
            dominated = False
            for other in valid_nodes:
                if other.id == cand.id:
                    continue
                # cand area vs other area
                c_area = cand.metrics.area_um2 or cand.metrics.gate_count or 1e9
                o_area = other.metrics.area_um2 or other.metrics.gate_count or 1e9
                c_wns = cand.metrics.wns_ns
                o_wns = other.metrics.wns_ns

                # other dominates cand if other has >= wns and <= area, with at least one strictly better
                if (o_wns >= c_wns and o_area <= c_area) and (o_wns > c_wns or o_area < c_area):
                    dominated = True
                    break
            if not dominated:
                pareto.append(cand)
        return pareto

    def get_best_design(self) -> Optional[SnapshotNode]:
        """
        Selects the best design: highest WNS with timing closure >= 0, then minimal area.
        """
        frontier = self.get_pareto_frontier()
        if not frontier:
            # Fallback to any passed simulation with best WNS
            passed = [n for n in self.nodes.values() if n.metrics.sim_passed]
            if not passed:
                return None
            return max(passed, key=lambda n: n.metrics.wns_ns if n.metrics.wns_ns is not None else -999.0)

        # Prefer timing closed (WNS >= 0.0) first, then least area
        closed = [n for n in frontier if (n.metrics.wns_ns or -1) >= 0.0]
        if closed:
            return min(closed, key=lambda n: n.metrics.area_um2 or n.metrics.gate_count or 1e9)
        return max(frontier, key=lambda n: n.metrics.wns_ns or -999.0)

    def export_summary(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "pareto_ids": [n.id for n in self.get_pareto_frontier()],
            "best_id": self.get_best_design().id if self.get_best_design() else None,
        }
