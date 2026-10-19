"""
SiliconForge Command-Line Interface.
Provides CLI commands to initialize workspaces, launch agent tournaments,
manage snapshots, and inspect experiment DAGs.
"""

from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path

from siliconforge.core.env import HardwareEnvironment
from siliconforge.core.tournament import ExplorationTournament
from siliconforge.vmm.firecracker import HypervisorManager


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="siliconforge",
        description="SiliconForge: Isolated Execution Platform for Autonomous Hardware Engineering"
    )
    subparsers = parser.add_subparsers(dest="command", help="SiliconForge subcommands")

    # Command: info
    subparsers.add_parser("info", help="Display system hypervisor capabilities and EDA environment")

    # Command: run-demo
    parser_demo = subparsers.add_parser("run-demo", help="Run the autonomous cache optimization tournament demo")
    parser_demo.add_argument("--example", default="01_riscv_cache_optimization", help="Example directory to run")

    args = parser.parse_args()

    if args.command == "info":
        backend = HypervisorManager.get_recommended_backend()
        kvm = HypervisorManager.is_kvm_available()
        print("SiliconForge System Info")
        print("------------------------")
        print(f"KVM Hardware Acceleration: {'Enabled (/dev/kvm)' if kvm else 'Disabled / Host Fallback'}")
        print(f"Active Virtualization Driver: {backend}")
        print("Supported EDA Engines: Verilator, Yosys, Icarus Verilog, OpenROAD")
    elif args.command == "run-demo":
        import importlib.util
        demo_path = Path(__file__).resolve().parent.parent.parent / "examples" / "01_riscv_cache_optimization" / "run_demo.py"
        spec = importlib.util.spec_from_file_location("run_demo", str(demo_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.run_showcase_demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
