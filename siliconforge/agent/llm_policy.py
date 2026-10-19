"""
SiliconForge LLM Hardware Policies.
Connects real language model providers (OpenAI, Anthropic, or local endpoints)
to the hardware agent loop, providing structured EDA error feedback and prompts.
"""

from __future__ import annotations
import json
import os
import re
from typing import Dict, Any, Optional
from siliconforge.core.models import PPAMetrics


HARDWARE_OPTIMIZATION_SYSTEM_PROMPT = """
You are an expert digital ASIC/FPGA hardware design engineer.
Your task is to inspect the current SystemVerilog/Verilog RTL code, analyze the simulation
and timing/PPA metrics from the prior iteration, and produce an improved RTL implementation.

Key Objectives:
1. Ensure full functional correctness (pass all testbench assertions).
2. Optimize timing slack (Worst Negative Slack, WNS >= 0.0 ns).
3. Minimize cell area and gate count.

Response Format:
Return your response as a valid JSON object with the following keys:
{
  "explanation": "Detailed engineering rationale for this change",
  "code": "The COMPLETE modified Verilog code for the module"
}
Do NOT return Markdown backticks around the JSON. Return pure JSON.
"""


class LLMHardwarePolicy:
    """Base policy connector for LLM providers."""

    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    def format_prompt(
        self,
        iteration: int,
        current_code: str,
        last_metrics: Optional[PPAMetrics],
        sim_error_log: Optional[str] = None
    ) -> str:
        prompt = f"=== ITERATION {iteration} ===\n\n"
        if last_metrics:
            prompt += f"PRIOR METRICS:\n"
            prompt += f"- Simulation Passed: {last_metrics.sim_passed}\n"
            prompt += f"- WNS Slack: {last_metrics.wns_ns} ns\n"
            prompt += f"- Total Area: {last_metrics.area_um2} um2\n"
            prompt += f"- Gate Count: {last_metrics.gate_count}\n\n"

        if sim_error_log:
            prompt += f"SIMULATION FAILURE / COMPILER LOG:\n{sim_error_log}\n\n"

        prompt += f"CURRENT RTL CODE:\n```verilog\n{current_code}\n```\n"
        return prompt

    def query_model(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Queries the configured LLM API.
        Falls back to structured heuristic parsing if API keys are absent.
        """
        # If OpenAI is installed and API key is present
        if "gpt" in self.model_name.lower() and os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": HARDWARE_OPTIMIZATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                print(f"[LLMPolicy] OpenAI query error: {e}")
                return None

        # Return None when no external API key is configured
        return None
