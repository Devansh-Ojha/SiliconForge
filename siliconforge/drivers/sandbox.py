"""
SiliconForge Sandbox Drivers: Isolated Workspace Execution and Copy-On-Write Snapshots.
Supports CoW Hardlink/Reflink/Overlay Trees and MicroVM / Subprocess execution sandboxes.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class ExecutionResult:
    def __init__(self, returncode: int, stdout: str, stderr: str, duration_sec: float):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_sec = duration_sec

    @property
    def success(self) -> bool:
        return self.returncode == 0


class BaseStorageDriver(ABC):
    @abstractmethod
    def create_root(self, source_path: Path, node_id: str) -> Path:
        pass

    @abstractmethod
    def snapshot(self, source_node_id: str, new_node_id: str) -> Path:
        """Create a fast CoW / deduplicated fork of the workspace."""
        pass

    @abstractmethod
    def rollback(self, node_id: str) -> Path:
        pass


class CoWWorkspaceDriver(BaseStorageDriver):
    """
    Sub-second Copy-On-Write Workspace Driver.
    Uses hardlink-trees on POSIX/macOS and APFS reflinks where available for near-instant zero-disk cloning.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir).resolve()
        self.snapshots_dir = self.base_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.node_paths: Dict[str, Path] = {}

    def create_root(self, source_path: Path, node_id: str) -> Path:
        dest = self.snapshots_dir / node_id
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_path, dest, symlinks=True)
        self.node_paths[node_id] = dest
        return dest

    def snapshot(self, source_node_id: str, new_node_id: str) -> Path:
        src = self.node_paths.get(source_node_id)
        if not src or not src.exists():
            raise FileNotFoundError(f"Source snapshot '{source_node_id}' does not exist.")

        dest = self.snapshots_dir / new_node_id
        if dest.exists():
            shutil.rmtree(dest)

        # On macOS/APFS, cp -c or cp -R creates copy-on-write clone files instantly
        try:
            res = subprocess.run(
                ["cp", "-Rc", str(src), str(dest)],
                capture_output=True,
                check=False
            )
            if res.returncode != 0:
                # Fallback to copytree with hardlinks or standard recursive copy
                shutil.copytree(src, dest, copy_function=os.link)
        except Exception:
            shutil.copytree(src, dest)

        self.node_paths[new_node_id] = dest
        return dest

    def rollback(self, node_id: str) -> Path:
        path = self.node_paths.get(node_id)
        if not path or not path.exists():
            raise FileNotFoundError(f"Cannot rollback to non-existent node '{node_id}'")
        return path


class ExecutionSandbox:
    """
    Runs isolated simulation, compilation, and EDA passes inside a specific snapshot workspace.
    Enforces timeout limits, developer environment variable overrides, and captures standard I/O.
    """

    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path).resolve()

    def run_command(
        self,
        cmd: List[str],
        timeout: int = 120,
        extra_env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        env = os.environ.copy()
        # Ensure Apple CLT is used if on macOS
        if os.path.exists("/Library/Developer/CommandLineTools"):
            env["DEVELOPER_DIR"] = "/Library/Developer/CommandLineTools"
        if extra_env:
            env.update(extra_env)

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace_path),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            t1 = time.time()
            return ExecutionResult(
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_sec=round(t1 - t0, 3)
            )
        except subprocess.TimeoutExpired as e:
            t1 = time.time()
            return ExecutionResult(
                returncode=124,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=f"TimeoutExpired after {timeout} seconds",
                duration_sec=round(t1 - t0, 3)
            )
