"""
SiliconForge MicroVM Manager.
Provides an abstraction over hypervisors (Firecracker, QEMU/KVM) for running
untrusted agent hardware workloads in isolated microVMs with sub-second snapshots.
"""

from __future__ import annotations
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List


@dataclass
class VmConfig:
    vm_id: str
    vcpu_count: int = 2
    mem_size_mib: int = 2048
    kernel_image_path: str = "/var/lib/siliconforge/vmlinux"
    rootfs_path: str = ""
    vsock_path: str = ""
    socket_path: str = ""
    enable_network: bool = False


class FirecrackerDriver:
    """
    Manages Firecracker microVM instances via Unix domain socket API.
    Supports microVM boot, snapshotting, and pause/resume.
    """

    def __init__(self, config: VmConfig):
        self.config = config
        self.proc: Optional[subprocess.Popen] = None
        self.socket_path = Path(config.socket_path or f"/tmp/fc_{config.vm_id}.sock")

    def _api_request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send raw HTTP-over-Unix-socket request to Firecracker daemon."""
        if not self.socket_path.exists():
            raise RuntimeError(f"Firecracker socket not found at {self.socket_path}")

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect(str(self.socket_path))
            body_bytes = json.dumps(body).encode() if body else b""
            req = (
                f"{method} {path} HTTP/1.1\r\n"
                f"Host: localhost\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body_bytes)}\r\n\r\n"
            ).encode() + body_bytes
            s.sendall(req)

            resp = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                resp += chunk

            resp_str = resp.decode("utf-8", errors="replace")
            # Parse HTTP response body
            parts = resp_str.split("\r\n\r\n", 1)
            if len(parts) > 1 and parts[1].strip():
                try:
                    return json.loads(parts[1])
                except json.JSONDecodeError:
                    return {"raw": parts[1]}
            return {"status": "ok"}
        finally:
            s.close()

    def start_daemon(self, firecracker_bin: str = "firecracker") -> None:
        """Spawns the Firecracker background daemon listening on the unix socket."""
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.proc = subprocess.Popen(
            [firecracker_bin, "--api-sock", str(self.socket_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Wait for socket creation
        for _ in range(50):
            if self.socket_path.exists():
                break
            time.sleep(0.02)

        if not self.socket_path.exists():
            raise TimeoutError("Firecracker failed to create API socket.")

    def configure_and_boot(self) -> None:
        """Configures machine, boot source, and root drive, then boots the VM."""
        # 1. Machine config
        self._api_request("PUT", "/machine-config", {
            "vcpu_count": self.config.vcpu_count,
            "mem_size_mib": self.config.mem_size_mib,
            "smt": False
        })

        # 2. Boot source
        self._api_request("PUT", "/boot-source", {
            "kernel_image_path": self.config.kernel_image_path,
            "boot_args": "console=ttyS0 reboot=k panic=1 pci=off init=/init"
        })

        # 3. Root drive
        self._api_request("PUT", "/drives/rootfs", {
            "drive_id": "rootfs",
            "path_on_host": self.config.rootfs_path,
            "is_root_device": True,
            "is_read_only": False
        })

        # 4. Instance Start
        self._api_request("PUT", "/actions", {"action_type": "InstanceStart"})

    def create_snapshot(self, mem_file_path: str, snapshot_path: str) -> None:
        """Pauses the VM and creates a stateful snapshot (RAM + CPU state)."""
        self._api_request("PATCH", "/vm", {"state": "Paused"})
        self._api_request("PUT", "/snapshot/create", {
            "snapshot_type": "Full",
            "snapshot_path": snapshot_path,
            "mem_file_path": mem_file_path
        })

    def resume(self) -> None:
        self._api_request("PATCH", "/vm", {"state": "Resumed"})

    def terminate(self) -> None:
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass


class HypervisorManager:
    """
    Auto-detects host virtualization capabilities (KVM vs Apple Hypervisor vs Local CoW).
    Provides a unified interface so code works across Linux servers and macOS laptops.
    """

    @staticmethod
    def is_kvm_available() -> bool:
        return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)

    @staticmethod
    def get_recommended_backend() -> str:
        if HypervisorManager.is_kvm_available():
            return "firecracker"
        return "cow_sandbox"
