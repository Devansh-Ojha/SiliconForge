"""
SiliconForge Waveform Anomaly & Counterexample Extractor.
Parses VCD (Value Change Dump) simulation traces, identifies error/assertion timestamps,
and extracts a localized temporal slice (+/- N cycles) into an ASCII timing diagram and tabular trace.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class WaveformSliceExtractor:
    """
    Extracts temporal windows around assertion failures from VCD files.
    Formats multi-signal values into compact ASCII waveforms and tables for LLM reasoning.
    """

    def __init__(self, vcd_path: Path):
        self.vcd_path = Path(vcd_path)
        self.signals: Dict[str, str] = {}        # code -> name
        self.signal_names: Dict[str, str] = {}   # name -> code
        self.timescale: str = "1ps"
        self.parsed = False
        self.events: List[Tuple[int, str, str]] = []  # (timestamp, code, value)

    def parse_header(self, lines: List[str]) -> int:
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("$var"):
                parts = line.split()
                if len(parts) >= 5:
                    sig_type, width, code, name = parts[1], parts[2], parts[3], parts[4]
                    self.signals[code] = name
                    self.signal_names[name] = code
            elif line.startswith("$timescale"):
                if idx + 1 < len(lines) and "$end" not in line:
                    self.timescale = lines[idx + 1].strip()
                else:
                    self.timescale = line
            elif line.startswith("$enddefinitions"):
                return idx + 1
            idx += 1
        return idx

    def parse_body(self) -> None:
        if not self.vcd_path.exists():
            raise FileNotFoundError(f"VCD file not found: {self.vcd_path}")

        lines = self.vcd_path.read_text(encoding="utf-8", errors="replace").splitlines()
        body_start = self.parse_header(lines)

        current_time = 0
        for i in range(body_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
            if line.startswith("#"):
                try:
                    current_time = int(line[1:])
                except ValueError:
                    pass
            elif line.startswith(("b", "B", "r", "R")):
                # Bus value change: b1010 code
                parts = line.split()
                if len(parts) == 2:
                    val, code = parts[0][1:], parts[1]
                    self.events.append((current_time, code, val))
            elif len(line) >= 2 and line[0] in ("0", "1", "x", "X", "z", "Z"):
                # Scalar value change: 1code
                val = line[0]
                code = line[1:]
                self.events.append((current_time, code, val))

        self.parsed = True

    def extract_anomaly_window(
        self,
        failure_time: int,
        target_signals: Optional[List[str]] = None,
        window_cycles: int = 5,
        clock_period: int = 10
    ) -> Dict[str, Any]:
        """
        Extracts a localized temporal slice around failure_time.
        Returns tabular values and ASCII timing diagram representation.
        """
        if not self.parsed:
            self.parse_body()

        start_time = max(0, failure_time - (window_cycles * clock_period))
        end_time = failure_time + (2 * clock_period)

        # Track signals of interest
        filter_codes = set()
        if target_signals:
            for sname in target_signals:
                if sname in self.signal_names:
                    filter_codes.add(self.signal_names[sname])
        else:
            filter_codes = set(self.signals.keys())

        # Sample signal state across regular clock ticks in the window
        sampled_times = list(range(start_time, end_time + 1, clock_period))
        signal_states: Dict[str, Dict[int, str]] = {
            self.signals[c]: {} for c in filter_codes if c in self.signals
        }

        # Compute signal values at each sampled time
        current_vals: Dict[str, str] = {c: "0" for c in filter_codes}
        event_idx = 0

        for t in sampled_times:
            while event_idx < len(self.events) and self.events[event_idx][0] <= t:
                _, code, val = self.events[event_idx]
                if code in filter_codes:
                    current_vals[code] = val
                event_idx += 1
            for code in filter_codes:
                if code in self.signals:
                    sname = self.signals[code]
                    signal_states[sname][t] = current_vals[code]

        # Generate ASCII trace diagram
        ascii_lines = []
        ascii_lines.append(f"Waveform Slice Around Anomaly (T={failure_time}):")
        time_header = "Time:    " + " ".join([f"{t:>6}" for t in sampled_times])
        ascii_lines.append(time_header)
        ascii_lines.append("-" * len(time_header))

        for sname, values in signal_states.items():
            line = f"{sname:<8} "
            for t in sampled_times:
                v = values.get(t, "-")
                line += f"{v:>6} "
            if sname in ("error", "resp_hit", "rst_n"):
                line += " <-- CRITICAL"
            ascii_lines.append(line)

        ascii_diagram = "\n".join(ascii_lines)

        return {
            "failure_time": failure_time,
            "window_start": start_time,
            "window_end": end_time,
            "sampled_times": sampled_times,
            "signals": signal_states,
            "ascii_diagram": ascii_diagram
        }
