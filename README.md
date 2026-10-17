# SiliconForge

**An isolated, snapshotting, agent-native execution platform for autonomous hardware development.**

SiliconForge gives AI coding agents an isolated, reproducible hardware development sandbox that they can checkpoint, fork, roll back, and explore in parallel across RTL simulation, synthesis, and physical design.

---

## Key Features

- **CoW Sub-second Snapshotting**: Near-instantaneous copy-on-write workspace cloning for branching agent exploration trees.
- **Experiment DAG & Pareto Frontier**: Automatically tracks multi-branch architectural exploration, pruning failures and ranking valid designs across Power, Performance, and Area (PPA).
- **Structured EDA Telemetry**: Converts verbose Verilator, Yosys, and OpenROAD logs into structured metrics (WNS, TNS, area, gate count, simulation cycles) formatted for LLM reasoning.
- **Rollback on Failure**: When an agent introduces a functional bug, syntax error, or timing violation, SiliconForge rolls back to the prior checkpoint without state pollution.

---

## Architecture Overview

```
                      ┌────────────────────────────┐
                      │    AI Hardware Agent       │
                      │  (Claude, GPT-4, DeepSeek) │
                      └─────────────┬──────────────┘
                                    │ Python SDK / CLI
                                    ▼
                      ┌────────────────────────────┐
                      │    ExplorationTournament   │
                      │     & Experiment DAG       │
                      └─────────────┬──────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
        ┌──────────────────┐                ┌──────────────────┐
        │  Branch Alpha    │                │  Branch Gamma    │
        │  (Faulty bypass) │                │  (Pipelined hit) │
        │  Status: FAILED  │                │  Status: PASSED  │
        │  -> ROLLED BACK  │                │  -> PARETO BEST  │
        └──────────────────┘                └──────────────────┘
```

---

## Quickstart & Demo

Run the autonomous RISC-V cache optimization tournament demo:

```bash
# Clone the repository
git clone git@github.com:Devansh-Ojha/SiliconForge.git
cd SiliconForge

# Run the tournament demo (using Verilator)
python3 examples/01_riscv_cache_optimization/run_demo.py
```

### Running Unit Tests

```bash
PYTHONPATH=. python3 tests/test_siliconforge.py
```

---

## Project Structure

```
SiliconForge/
├── siliconforge/
│   ├── core/
│   │   ├── models.py       # SnapshotNode, PPAMetrics, NodeStatus
│   │   ├── dag.py          # ExperimentDAG and Pareto frontier engine
│   │   ├── env.py          # High-level HardwareEnvironment API
│   │   └── tournament.py   # Multi-agent tournament search orchestrator
│   ├── drivers/
│   │   └── sandbox.py      # CoW workspace driver & execution sandboxes
│   └── telemetry/
│       └── parsers.py      # Verilator, Yosys & OpenROAD telemetry parsers
├── examples/
│   └── 01_riscv_cache_optimization/
│       ├── riscv_cache.v   # Parameterized RISC-V cache RTL
│       ├── sim_main.cpp    # C++ testbench for Verilator
│       ├── Makefile        # Compilation & simulation flow
│       └── run_demo.py     # Multi-branch tournament demo
└── tests/
    └── test_siliconforge.py # Complete core test suite
```