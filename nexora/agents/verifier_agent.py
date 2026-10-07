"""
Verifier Agent for NEXORA-8.
Executes test suites and performs strict regression comparison.
"""

from typing import Optional
from nexora.agents.base import BaseAgent, AgentStatus
from nexora.verifier.regression_detector import RegressionDetector, VerificationVerdict
from nexora.verifier.test_runner import TestRunner, TestResult


class VerifierAgent(BaseAgent):
    """Executes sandboxed tests and certifies that zero regressions occurred."""

    def __init__(self):
        super().__init__(name="Verifier", role_description="Runs pytest suite and deterministically certifies zero regressions")

    def run_baseline(self, runner: TestRunner) -> TestResult:
        self.set_status(AgentStatus.WORKING, "Executing baseline test suite...")
        res = runner.run_tests()
        self.log(f"Baseline test run: {res.passed_count} passed, {res.failed_count} failed, {res.error_count} error(s).")
        self.set_status(AgentStatus.COMPLETED, f"Baseline captured ({res.passed_count}/{res.total_tests} passed).")
        return res

    def verify_patch(self, runner: TestRunner, baseline_result: TestResult) -> tuple[TestResult, VerificationVerdict]:
        self.set_status(AgentStatus.WORKING, "Executing verification test suite on patched code...")
        post_result = runner.run_tests()
        verdict = RegressionDetector.compare(baseline_result, post_result)

        if verdict.has_regressions:
            self.set_status(AgentStatus.FAILED, f"REGRESSION: {len(verdict.regressions)} test(s) broke!")
            self.log(f"Broken tests: {', '.join(verdict.regressions)}")
        elif verdict.is_verified:
            self.set_status(AgentStatus.COMPLETED, f"Verified safe: {post_result.passed_count}/{post_result.total_tests} passing, 0 regressions.")
            self.log(verdict.message)
        else:
            self.set_status(AgentStatus.FAILED, f"Verification incomplete: {post_result.failed_count} test(s) failed.")
            self.log(verdict.message)

        return post_result, verdict
