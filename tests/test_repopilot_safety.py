import tempfile
from pathlib import Path

import pytest

from nexora.verifier.regression_detector import RegressionDetector
from nexora.verifier.sandbox import SandboxRunner
from nexora.verifier.test_runner import TestResult


def test_existing_tests_are_protected_but_new_tests_are_allowed():
    with tempfile.TemporaryDirectory() as root:
        Path(root, "tests").mkdir()
        Path(root, "tests", "test_existing.py").write_text("def test_existing(): pass\n", encoding="utf-8")
        sandbox = SandboxRunner(root)
        sandbox.setup()
        with pytest.raises(PermissionError, match="PROTECTED TEST FILE"):
            sandbox.write_file("tests/test_existing.py", "def test_existing(): assert False\n")
        sandbox.write_file("tests/test_generated.py", "def test_generated(): assert True\n")
        sandbox.cleanup()


def test_preexisting_failures_are_not_reported_as_regressions():
    baseline = TestResult(False, 2, 1, 1, 0, 0, 0.1, passed_test_ids={"test_ok"}, failed_test_ids={"test_existing_failure"}, return_code=1)
    post = TestResult(False, 3, 2, 1, 0, 0, 0.1, passed_test_ids={"test_ok", "test_new"}, failed_test_ids={"test_existing_failure"}, return_code=1)
    verdict = RegressionDetector.compare(baseline, post)
    assert not verdict.has_regressions
    assert verdict.baseline_failures == ["test_existing_failure"]
    assert verdict.unchanged_failures == ["test_existing_failure"]
    assert not verdict.is_verified
