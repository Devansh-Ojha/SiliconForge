"""
SiliconForge Core Types: Snapshot DAG, Experiment Tree, and Results.
"""

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class NodeStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    PRUNED = "PRUNED"


@dataclass
class PPAMetrics:
    """Power, Performance, Area and timing telemetry."""
    wns_ns: Optional[float] = None          # Worst Negative Slack (ns)
    tns_ns: Optional[float] = None          # Total Negative Slack (ns)
    area_um2: Optional[float] = None        # Total Cell Area
    gate_count: Optional[int] = None        # Equivalent Logic Gates
    dynamic_power_mw: Optional[float] = None
    leakage_power_mw: Optional[float] = None
    sim_cycles: Optional[int] = None
    sim_time_sec: Optional[float] = None
    sim_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wns_ns": self.wns_ns,
            "tns_ns": self.tns_ns,
            "area_um2": self.area_um2,
            "gate_count": self.gate_count,
            "dynamic_power_mw": self.dynamic_power_mw,
            "leakage_power_mw": self.leakage_power_mw,
            "sim_cycles": self.sim_cycles,
            "sim_time_sec": self.sim_time_sec,
            "sim_passed": self.sim_passed,
        }


@dataclass
class SnapshotNode:
    """A single node in the SiliconForge Experiment DAG."""
    id: str = field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:10]}")
    parent_id: Optional[str] = None
    name: str = "checkpoint"
    description: str = ""
    status: NodeStatus = NodeStatus.INITIALIZED
    created_at: float = field(default_factory=time.time)
    storage_path: str = ""
    diff_from_parent: Optional[str] = None
    metrics: PPAMetrics = field(default_factory=PPAMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    children_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "storage_path": self.storage_path,
            "diff_from_parent": self.diff_from_parent,
            "metrics": self.metrics.to_dict(),
            "metadata": self.metadata,
            "children_ids": self.children_ids,
        }
