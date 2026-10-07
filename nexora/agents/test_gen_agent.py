"""
Test Generator Agent for NEXORA-8.
Generates meaningful pytest test cases covering the newly implemented change.
"""

from dataclasses import dataclass
import os
import re
from typing import Dict, List, Optional
from nexora.agents.base import BaseAgent, AgentStatus
from nexora.agents.planner import RepairPlan
from nexora.llm.client import LLMClient
from nexora.verifier.sandbox import SandboxRunner
from nexora.verifier.test_runner import TestRunner, TestResult


@dataclass
class GeneratedTestSuite:
    __test__ = False
    file_path: str
    test_code: str
    passed: bool
    test_count: int
    output: str


class TestGenAgent(BaseAgent):
    """Generates and executes tests for newly implemented bug fixes and features."""
    __test__ = False

    def __init__(self, llm_client: LLMClient):
        super().__init__(name="TestGenerator", role_description="Generates automated pytest test cases for implemented changes")
        self.llm_client = llm_client

    def generate_and_verify(
        self,
        sandbox: SandboxRunner,
        runner: TestRunner,
        task_description: str,
        plan: RepairPlan,
        modified_files: List[str],
    ) -> GeneratedTestSuite:
        self.set_status(AgentStatus.WORKING, "Generating new pytest regression test cases...")

        # Read modified files to provide context
        context_code = ""
        for mf in modified_files[:2]:
            try:
                c = sandbox.read_file(mf)
                context_code += f"\n# File: {mf}\n" + c + "\n"
            except Exception:
                pass

        prompt = f"""You are an expert software engineer writing pytest unit tests.
TASK: {task_description}
STRATEGY: {plan.strategy}
ROOT CAUSE: {plan.root_cause}

MODIFIED CODE CONTEXT:
{context_code}

INSTRUCTIONS:
1. Write 1 to 3 targeted pytest test functions that test the newly fixed or added behavior.
2. Ensure imports are correct and relative/package paths work properly.
3. Include assertions that specifically check boundary conditions and expected return values.
4. Output ONLY clean Python code. Do not include markdown codeblocks if possible, or wrap in ```python.
"""
        response = self.llm_client.generate(prompt=prompt, system_prompt="You are a professional pytest developer. Write clean test code only.")
        test_code = self._clean_code(response.content)

        # Write to sandbox test file
        test_rel_path = "tests/test_nexora_acceptance.py"
        sandbox.write_file(test_rel_path, test_code)
        self.log(f"Wrote generated test suite to {test_rel_path}")

        # Execute only the generated test file to verify it passes
        test_res = runner.run_tests(target_path=test_rel_path)

        if test_res.passed:
            self.set_status(AgentStatus.COMPLETED, f"Generated tests verified: {test_res.passed_count} test(s) passed.", data={
                "file_path": test_rel_path,
                "passed_count": test_res.passed_count,
            })
            self.log(f"Generated test suite successfully passed ({test_res.passed_count}/{test_res.total_tests}).")
        else:
            self.set_status(AgentStatus.FAILED, f"Generated test failed: {test_res.failed_count} failures.", data={
                "file_path": test_rel_path,
                "raw_output": test_res.raw_output,
            })
            self.log(f"Generated test failed to pass against patched code: {test_res.raw_output[:200]}")

        return GeneratedTestSuite(
            file_path=test_rel_path,
            test_code=test_code,
            passed=test_res.passed,
            test_count=test_res.total_tests,
            output=test_res.raw_output,
        )

    def _clean_code(self, raw: str) -> str:
        # Strip markdown fences
        if "```python" in raw:
            parts = raw.split("```python")
            raw = parts[1].split("```")[0]
        elif "```" in raw:
            parts = raw.split("```")
            raw = parts[1].split("```")[0]
        return raw.strip()
