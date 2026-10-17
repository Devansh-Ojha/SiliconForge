"""
Structured EDA Telemetry Parsers.
Converts noisy, verbose EDA/simulation logs (Verilator, Yosys, OpenROAD) into structured,
compact telemetry schemas ideal for LLM context windows and objective scoring.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional
from siliconforge.core.models import PPAMetrics


class VerilatorLogParser:
    """Parses Verilator compilation and simulation outputs."""

    @staticmethod
    def parse_simulation_output(stdout: str, stderr: str) -> PPAMetrics:
        combined = f"{stdout}\n{stderr}"
        metrics = PPAMetrics()

        # Check for standard testbench completion markers
        if "ALL TESTS PASSED" in combined or "TEST PASSED" in combined or "SUCCESS" in combined:
            metrics.sim_passed = True
        elif "TEST FAILED" in combined or "ASSERTION FAILED" in combined or "%Error" in combined:
            metrics.sim_passed = False

        # Extract cycle count if printed (e.g., "[CYCLES: 1042]")
        cycle_match = re.search(r"CYCLES[:\s=]+(\d+)", combined, re.IGNORECASE)
        if cycle_match:
            metrics.sim_cycles = int(cycle_match.group(1))

        # Extract execution time if printed (e.g., "[TIME: 4.25s]")
        time_match = re.search(r"SIM_TIME[:\s=]+([\d\.]+)\s*(?:s|sec)?", combined, re.IGNORECASE)
        if time_match:
            metrics.sim_time_sec = float(time_match.group(1))

        return metrics

    @staticmethod
    def extract_errors_and_warnings(stderr: str) -> Dict[str, List[str]]:
        errors = []
        warnings = []
        for line in stderr.splitlines():
            line_str = line.strip()
            if "%Error" in line_str:
                errors.append(line_str)
            elif "%Warning" in line_str:
                warnings.append(line_str)
        return {"errors": errors, "warnings": warnings}


class YosysLogParser:
    """Parses Yosys synthesis logs for gate count and estimated cell area."""

    @staticmethod
    def parse_synthesis(stdout: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "gate_count": 0,
            "chip_area": 0.0,
            "cells": {}
        }

        # Match "Number of cells: 142"
        cells_match = re.search(r"Number of cells:\s+(\d+)", stdout)
        if cells_match:
            info["gate_count"] = int(cells_match.group(1))

        # Match "Chip area for module ...: 1250.40"
        area_match = re.search(r"Chip area for module.*?:\s+([\d\.]+)", stdout)
        if area_match:
            info["chip_area"] = float(area_match.group(1))

        return info


class OpenROADTimingParser:
    """Parses OpenROAD or static timing analysis (STA) reports for WNS / TNS."""

    @staticmethod
    def parse_timing_report(report_text: str) -> Dict[str, Optional[float]]:
        # Match "wns -0.42" or "worst negative slack -0.42" or "slack (VIOLATED) -0.42"
        wns = None
        tns = None

        wns_match = re.search(r"(?:wns|worst negative slack|slack \(VIOLATED\)|slack \(MET\))[:\s]+([-\d\.]+)", report_text, re.IGNORECASE)
        if wns_match:
            try:
                wns = float(wns_match.group(1))
            except ValueError:
                pass

        tns_match = re.search(r"(?:tns|total negative slack)[:\s]+([-\d\.]+)", report_text, re.IGNORECASE)
        if tns_match:
            try:
                tns = float(tns_match.group(1))
            except ValueError:
                pass

        return {"wns_ns": wns, "tns_ns": tns}
