"""
Planner Agent for NEXORA-8.
Performs root cause analysis and formulates minimal modification plans.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Dict, List, Optional
from nexora.agents.base import BaseAgent, AgentStatus
from nexora.analyzer.retrieval import RetrievedCandidate
from nexora.llm.client import LLMClient


@dataclass
class RepairPlan:
    root_cause: str
    target_files: List[str]
    target_symbols: List[str]
    strategy: str
    reasoning: str

    def to_dict(self) -> Dict:
        return {
            "root_cause": self.root_cause,
            "target_files": self.target_files,
            "target_symbols": self.target_symbols,
            "strategy": self.strategy,
            "reasoning": self.reasoning,
        }


class PlannerAgent(BaseAgent):
    """Generates structured Root Cause Analysis and modification strategy."""

    def __init__(self, llm_client: LLMClient):
        super().__init__(name="Planner", role_description="Analyzes code defects and designs safe modification plans")
        self.llm_client = llm_client

    def plan(
        self,
        task_description: str,
        candidates: List[RetrievedCandidate],
        failing_tests_summary: Optional[str] = None,
    ) -> RepairPlan:
        self.set_status(AgentStatus.WORKING, "Formulating Root Cause Analysis and modification plan...")

        snippets_text = ""
        for c in candidates[:3]:
            snippets_text += f"\n--- File: {c.relative_path} (Relevance Score: {c.score}) ---\n"
            snippets_text += c.snippet + "\n"

        prompt = f"""You are an expert AI software engineering planner.
TASK DESCRIPTION:
{task_description}

RELEVANT CODE CANDIDATES:
{snippets_text}

FAILING TESTS (IF ANY):
{failing_tests_summary or "None reported initially."}

Instructions:
1. Identify the suspected root cause of the bug or feature requirement.
2. Specify the exact minimal target file(s) and function(s) to change.
3. Formulate a targeted strategy that preserves all existing workflows.
4. Output STRICT JSON with this schema:
{{
  "root_cause": "<concise explanation>",
  "target_files": ["<file1.py>"],
  "target_symbols": ["<func_name>"],
  "strategy": "<precise change plan>",
  "reasoning": "<why this fix is safe and minimal>"
}}
"""
        response = self.llm_client.generate(prompt=prompt, system_prompt="You are a precise software engineering planner. Return valid JSON only.")
        plan_dict = self._parse_json_plan(response.content)

        # Validate target files against existing candidate files
        target_files = plan_dict.get("target_files", [])
        if candidates:
            cand_paths = [c.relative_path for c in candidates]
            # If planned target files don't exist in candidate list, pick best candidate
            if not target_files or not any(tf in cand_paths for tf in target_files):
                target_files = [candidates[0].relative_path]

        plan = RepairPlan(
            root_cause=plan_dict.get("root_cause", "Identified behavioral defect in target function."),
            target_files=target_files,
            target_symbols=plan_dict.get("target_symbols", []),
            strategy=plan_dict.get("strategy", "Apply minimal input validation and logic correction."),
            reasoning=plan_dict.get("reasoning", "Ensures existing callers and test cases remain unbroken."),
        )

        self.log(f"Plan formulated: Root cause: {plan.root_cause}")
        self.log(f"Target files: {', '.join(plan.target_files)}")
        self.set_status(AgentStatus.COMPLETED, "Planning completed.", data=plan.to_dict())

        return plan

    def _parse_json_plan(self, content: str) -> Dict:
        try:
            # Look for JSON codeblock
            m = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            m2 = re.search(r'(\{.*\})', content, re.DOTALL)
            if m2:
                return json.loads(m2.group(1))
            return json.loads(content)
        except Exception:
            return {}
