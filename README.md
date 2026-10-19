# SiliconForge

An isolated, snapshotting, agent-native execution platform for autonomous hardware development.

[![SiliconForge CI](https://github.com/Devansh-Ojha/SiliconForge/actions/workflows/ci.yml/badge.svg)](https://github.com/Devansh-Ojha/SiliconForge/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## The Vision

Developing hardware with AI coding agents requires more than generating Verilog files. RTL simulation, logic synthesis, and physical design are compute-heavy, stateful, and non-linear.

SiliconForge gives AI hardware agents an isolated, reproducible development environment that they can checkpoint, fork, roll back, and run in parallel tournaments to optimize hardware across Power, Performance, and Area (PPA).

Think: VM and container infrastructure + Hardware toolchains + Autonomous AI agents, purpose-built for silicon engineering.

---

## Key Architectural Capabilities

- **Sub-second Copy-on-Write Snapshots**: Near-instantaneous workspace branching using APFS clones (macOS), Linux reflinks (Btrfs/XFS/ZFS), or Firecracker microVM snapshots.
- **Experiment DAG & Multi-Objective Pareto Frontier**: Tracks every micro-architectural exploration branch. Automatically filters out functional simulation bugs and ranks valid designs across timing slack (Worst Negative Slack, WNS) and cell area.
- **Structured EDA Telemetry Bus**: Transforms noisy compiler and synthesis outputs (Verilator, Yosys, OpenROAD) into structured, compact JSON schemas tailored for LLM reasoning windows.
- **Deterministic Rollback**: If an agent introduces a hazard bug, syntax fault, or timing violation, SiliconForge instantly rolls back to the parent checkpoint without polluting the workspace.
- **Isolated Execution Sandboxes**: Supports Firecracker microVMs over Unix domain sockets (`vsock`) with KVM hardware acceleration, as well as lightweight local isolation for development.

---

## Architecture

```
                      ┌───────────────────────────────────────┐
                      │          SiliconForge CLI / SDK       │
                      │     (AutonomousHardwareAgent / LLM)   │
                      └──────────────────┬────────────────────┘
                                         │
                                         ▼
                      ┌───────────────────────────────────────┐
                      │          ExplorationTournament        │
                      │            & Experiment DAG           │
                      └──────┬─────────────────────────┬──────┘
                             │                         │
              CoW Storage Driver                  VMM Manager
           (reflink / APFS / ext4)          (Firecracker / Sandboxes)
                             │                         │
                             └───────────┬─────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────────┐
                 │        Isolated Hardware Sandbox Worker         │
                 │                                                 │
                 │  - Verilator (C++ Cycle-Accurate Sim)           │
                 │  - Yosys (Logic Synthesis & Gate Counts)        │
                 │  - OpenROAD (Physical Design & STA Timing)      │
                 │  - Telemetry Parsers (WNS, Area, Assertions)    │
                 └─────────────────────────────────────────────────┘
```

---

## Installation

```bash
# Clone the repository
git clone git@github.com:Devansh-Ojha/SiliconForge.git
cd SiliconForge

# Install SiliconForge locally
pip install -e .

# (Optional) Install LLM provider dependencies (OpenAI, Anthropic)
pip install -e ".[llm]"
```

---

## Quickstart: Running the Tournament Demo

SiliconForge includes an end-to-end multi-branch optimization tournament on a parameterized RISC-V L1 Cache:

```bash
siliconforge run-demo
```

### What the Demo Does:
1. Initializes a clean baseline environment with RISC-V cache RTL (`riscv_cache.v`) and a Verilator testbench (`sim_main.cpp`).
2. Concurrent CoW snapshot forking of 3 agent exploration branches:
   - **Branch Alpha (Faulty)**: Aggressive tag-bypass logic with planted bug -> Fails simulation -> Rolled back.
   - **Branch Beta (Feasible)**: Dual-banked redundant cache -> Passes sim, but high cell area.
   - **Branch Gamma (Winner)**: Pipelined hit detection -> Passes sim, closes timing (WNS = +0.22 ns), optimal area -> Pareto Best.
3. Renders the experiment DAG and results table in the terminal:

```
+-------------------------------------------------------------------------------+
| riscv_cache_baseline (snap_base) (WNS: +0.00ns Area: 1000)                   |
| |-- agent_alpha_bypass (snap_alpha) [FAILED -> ROLLED BACK]                   |
| |-- agent_beta_redundant (snap_beta) (WNS: +0.08ns Area: 1850)                |
| \-- agent_gamma_pipelined (snap_gamma) (WNS: +0.22ns Area: 1150) [PARETO BEST]|
+-------------------------------------------------------------------------------+
```

---

## CLI Usage

```bash
# Display virtualization capabilities and detected EDA tools
siliconforge info

# Run autonomous cache optimization tournament
siliconforge run-demo
```

---

## Testing

SiliconForge includes a comprehensive unit test suite covering the Experiment DAG, telemetry parsers, synthesis scripts, hypervisor detection, and agent rollback loops:

```bash
# Run core test suite
PYTHONPATH=. python3 tests/test_siliconforge.py
PYTHONPATH=. python3 tests/test_vmm_synthesis.py
PYTHONPATH=. python3 tests/test_agent.py
```

---

## Repository Structure

```
SiliconForge/
├── siliconforge/
│   ├── core/
│   │   ├── models.py         # SnapshotNode, PPAMetrics, NodeStatus
│   │   ├── dag.py            # ExperimentDAG & Pareto frontier engine
│   │   ├── env.py            # HardwareEnvironment high-level SDK
│   │   └── tournament.py     # Multi-agent tournament orchestrator
│   ├── drivers/
│   │   └── sandbox.py        # CoW workspace driver & execution sandboxes
│   ├── vmm/
│   │   └── firecracker.py    # MicroVM manager & REST API bindings
│   ├── telemetry/
│   │   ├── parsers.py        # Verilator, Yosys & OpenROAD telemetry parsers
│   │   └── synthesis.py      # Automated Yosys synthesis scripting engine
│   ├── agent/
│   │   ├── hardware_agent.py # AutonomousHardwareAgent with rollback loop
│   │   └── llm_policy.py     # LLM provider connector & EDA prompt templates
│   └── cli/
│       ├── main.py           # CLI entrypoint (siliconforge)
│       └── visualizer.py     # Rich terminal DAG visualizer
├── guest-images/
│   ├── Dockerfile.eda        # Complete open-source EDA rootfs
│   └── build-rootfs.sh       # Script to build minimal ext4 images for Firecracker
├── examples/
│   └── 01_riscv_cache_optimization/
│       ├── riscv_cache.v     # Parameterized RISC-V cache RTL
│       ├── sim_main.cpp      # C++ cycle-accurate testbench
│       ├── Makefile          # Verilator compilation and run flow
│       └── run_demo.py       # Tournament execution script
├── tests/                    # Comprehensive unit tests
└── pyproject.toml            # Package configuration
```

---

## License

SiliconForge is licensed under the Apache 2.0 License.