"""
SiliconForge Experiment Visualizer.
Renders interactive terminal-based trees and summary tables using Rich.
"""

from __future__ import annotations
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel

from siliconforge.core.dag import ExperimentDAG
from siliconforge.core.models import SnapshotNode, NodeStatus


class DAGVisualizer:
    """Renders Experiment DAGs into rich terminal trees and Pareto tables."""

    def __init__(self, dag: ExperimentDAG, console: Optional[Console] = None):
        self.dag = dag
        self.console = console or Console()

    def render_tree(self) -> Tree:
        if not self.dag.root_id or self.dag.root_id not in self.dag.nodes:
            tree = Tree("[bold red]Empty Experiment DAG[/bold red]")
            return tree

        root_node = self.dag.nodes[self.dag.root_id]
        root_label = self._format_node_label(root_node)
        tree = Tree(root_label)

        def add_children(parent_node: SnapshotNode, current_tree: Tree):
            for cid in parent_node.children_ids:
                child = self.dag.get_node(cid)
                if child:
                    child_tree = current_tree.add(self._format_node_label(child))
                    add_children(child, child_tree)

        add_children(root_node, tree)
        return tree

    def _format_node_label(self, node: SnapshotNode) -> str:
        color = "green" if node.status == NodeStatus.SUCCESS else ("red" if node.status == NodeStatus.FAILED else "yellow")
        slack_str = f"WNS: {node.metrics.wns_ns:+.2f}ns" if node.metrics.wns_ns is not None else ""
        area_str = f"Area: {node.metrics.area_um2:.0f}" if node.metrics.area_um2 is not None else ""
        metrics_tag = f"[dim]({slack_str} {area_str})[/dim]" if (slack_str or area_str) else ""

        pareto_ids = [n.id for n in self.dag.get_pareto_frontier()]
        is_pareto = "★ [bold yellow]PARETO BEST[/bold yellow] " if node.id in pareto_ids and node.status == NodeStatus.SUCCESS else ""

        return f"[{color}]{node.name}[/{color}] [dim]({node.id})[/dim] {metrics_tag} {is_pareto}"

    def display(self) -> None:
        self.console.print(Panel(self.render_tree(), title="SiliconForge Experiment Lineage", border_style="cyan"))
