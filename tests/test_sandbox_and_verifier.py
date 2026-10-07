"""
Tests for SandboxRunner, TestRunner, and RegressionDetector.
"""

import os
import tempfile
import pytest
from nexora.verifier.sandbox import SandboxRunner
from nexora.verifier.test_runner import TestRunner, TestResult, TestCaseStatus
from nexora.verifier.regression_detector import RegressionDetector


def test_sandbox_isolation_and_rollback():
    with tempfile.TemporaryDirectory() as orig_dir:
        test_file = os.path.join(orig_dir, "app.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def func(): return 1\n")

        sandbox = SandboxRunner(orig_dir)
        sandbox_dir = sandbox.setup()

        # Modify file in sandbox
        sandbox.write_file("app.py", "def func(): return 2\n")
        assert "return 2" in sandbox.read_file("app.py")
        
        # Original file should be unchanged!
        with open(test_file, "r") as f:
            assert "return 1" in f.read()

        # Rollback
        sandbox.rollback_all()
        assert "return 1" in sandbox.read_file("app.py")

        sandbox.cleanup()


def test_regression_detector_detects_broken_tests():
    baseline = TestResult(
        passed=True,
        total_tests=2,
        passed_count=2,
        failed_count=0,
        skipped_count=0,
        error_count=0,
        duration=0.1,
        passed_test_ids={"tests/test_a.py::test_1", "tests/test_a.py::test_2"},
    )

    # Post-patch test_2 fails
    post_patch = TestResult(
        passed=False,
        total_tests=2,
        passed_count=1,
        failed_count=1,
        skipped_count=0,
        error_count=0,
        duration=0.1,
        passed_test_ids={"tests/test_a.py::test_1"},
        failed_test_ids={"tests/test_a.py::test_2"},
    )

    verdict = RegressionDetector.compare(baseline, post_patch)
    assert verdict.has_regressions
    assert not verdict.is_verified
    assert "tests/test_a.py::test_2" in verdict.regressions
