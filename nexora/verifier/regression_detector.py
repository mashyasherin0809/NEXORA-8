"""
Deterministic Regression Detection Matrix for NEXORA-8.
Strictly ensures zero regressions across the existing test suite.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from nexora.verifier.test_runner import TestResult


@dataclass
class VerificationVerdict:
    is_verified: bool
    has_regressions: bool
    regressions: List[str] = field(default_factory=list)
    fixed_tests: List[str] = field(default_factory=list)
    new_passed_tests: List[str] = field(default_factory=list)
    baseline_passed_count: int = 0
    final_passed_count: int = 0
    total_suite_count: int = 0
    baseline_failures: List[str] = field(default_factory=list)
    unchanged_failures: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict:
        return {
            "is_verified": self.is_verified,
            "has_regressions": self.has_regressions,
            "regressions": self.regressions,
            "fixed_tests": self.fixed_tests,
            "new_passed_tests": self.new_passed_tests,
            "baseline_passed_count": self.baseline_passed_count,
            "final_passed_count": self.final_passed_count,
            "total_suite_count": self.total_suite_count,
            "baseline_failures": self.baseline_failures,
            "unchanged_failures": self.unchanged_failures,
            "message": self.message,
        }


class RegressionDetector:
    """Compares baseline test suite against post-patch test suite."""

    @staticmethod
    def compare(baseline: TestResult, post_patch: TestResult) -> VerificationVerdict:
        baseline_passed = baseline.passed_test_ids
        post_passed = post_patch.passed_test_ids
        post_failed = post_patch.failed_test_ids

        # Regressions: tests that passed before but are now failing or missing
        regressions_set = baseline_passed.intersection(post_failed)
        missing_passed = baseline_passed - post_passed
        # Combine
        total_regressions = sorted(list(regressions_set.union(missing_passed)))

        # Fixed tests: tests that failed in baseline but now pass
        fixed_set = baseline.failed_test_ids.intersection(post_passed)
        fixed_tests = sorted(list(fixed_set))

        # Newly passing tests (e.g. from generated acceptance tests)
        new_passed = sorted(list(post_passed - baseline_passed))

        baseline_failures = sorted(baseline.failed_test_ids)
        unchanged_failures = sorted(set(baseline.failed_test_ids).intersection(post_patch.failed_test_ids))
        has_regressions = len(total_regressions) > 0
        # Existing failures are recorded, not treated as regressions. A patch is
        # safe when it preserves all baseline-passing tests and introduces no new failure.
        newly_failed = set(post_patch.failed_test_ids) - set(baseline.failed_test_ids)
        is_verified = (not has_regressions) and (not newly_failed) and post_patch.return_code == 0

        if has_regressions:
            message = f"CRITICAL REGRESSION DETECTED: {len(total_regressions)} previously passing test(s) failed after patch: {', '.join(total_regressions[:3])}"
        elif fixed_tests:
            message = f"VERIFICATION SUCCESS: Fixed {len(fixed_tests)} test(s) with 0 regressions ({post_patch.passed_count}/{post_patch.total_tests} passing)."
        else:
            suffix = f"; {len(unchanged_failures)} pre-existing failure(s) unchanged" if unchanged_failures else ""
            message = f"VERIFICATION SUCCESS: 0 regressions ({post_patch.passed_count}/{post_patch.total_tests} passing){suffix}."

        return VerificationVerdict(
            is_verified=is_verified,
            has_regressions=has_regressions,
            regressions=total_regressions,
            fixed_tests=fixed_tests,
            new_passed_tests=new_passed,
            baseline_passed_count=baseline.passed_count,
            final_passed_count=post_patch.passed_count,
            total_suite_count=post_patch.total_tests,
            baseline_failures=baseline_failures,
            unchanged_failures=unchanged_failures,
            message=message,
        )
