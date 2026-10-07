"""
End-to-end integration test for NEXORA-8 Agent.
"""

import os
import tempfile
import pytest
from nexora.config import Config
from nexora.agents.orchestrator import OrchestratorAgent


def test_end_to_end_repair_workflow():
    with tempfile.TemporaryDirectory() as repo_dir:
        # Create a sample project with a bug
        calc_file = os.path.join(repo_dir, "calc.py")
        with open(calc_file, "w", encoding="utf-8") as f:
            f.write(
                "def add(a, b):\n"
                "    return a - b  # Bug: subtraction instead of addition\n\n"
                "def multiply(a, b):\n"
                "    return a * b\n"
            )

        test_file = os.path.join(repo_dir, "test_calc.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                "from calc import add, multiply\n\n"
                "def test_multiply():\n"
                "    assert multiply(3, 4) == 12\n\n"
                "def test_add():\n"
                "    assert add(2, 3) == 5\n"
            )

        cfg = Config(model_provider="heuristic", max_repair_attempts=2)
        orchestrator = OrchestratorAgent(cfg)

        session = orchestrator.execute_task(
            repo_path=repo_dir,
            task_description="Fix the add function which returns wrong result due to subtraction",
            apply_to_original=False,
        )

        assert session.session_id.startswith("ses_")
        assert session.plan is not None
        assert session.baseline_tests is not None
        assert session.evidence_report is not None
