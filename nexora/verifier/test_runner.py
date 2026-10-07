"""
Pytest Test Suite Execution and Parsing Engine for NEXORA-8.
"""

from dataclasses import dataclass, field
import json
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set


@dataclass
class TestCaseStatus:
    __test__ = False
    nodeid: str  # e.g. tests/test_calc.py::test_add
    name: str
    status: str  # "passed", "failed", "error", "skipped"
    duration: float = 0.0
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestResult:
    __test__ = False
    passed: bool
    total_tests: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_count: int
    duration: float
    test_cases: List[TestCaseStatus] = field(default_factory=list)
    passed_test_ids: Set[str] = field(default_factory=set)
    failed_test_ids: Set[str] = field(default_factory=set)
    raw_output: str = ""
    timed_out: bool = False
    return_code: int = 0
    no_tests: bool = False

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "total_tests": self.total_tests,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "duration": round(self.duration, 2),
            "timed_out": self.timed_out,
            "return_code": self.return_code,
            "no_tests": self.no_tests,
            "test_cases": [
                {
                    "nodeid": tc.nodeid,
                    "name": tc.name,
                    "status": tc.status,
                    "duration": tc.duration,
                    "message": tc.message,
                }
                for tc in self.test_cases
            ],
            "passed_test_ids": sorted(list(self.passed_test_ids)),
            "failed_test_ids": sorted(list(self.failed_test_ids)),
        }


class TestRunner:
    """Executes pytest in a sandbox directory and parses structured results."""
    __test__ = False

    def __init__(self, sandbox_dir: str, timeout_seconds: int = 45):
        self.sandbox_dir = sandbox_dir
        self.timeout_seconds = timeout_seconds

    def run_tests(self, target_path: Optional[str] = None, extra_args: Optional[List[str]] = None) -> TestResult:
        """Run pytest inside the sandbox."""
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"]
        
        if target_path:
            cmd.append(target_path)
        if extra_args:
            cmd.extend(extra_args)

        env = os.environ.copy()
        # Add sandbox directory and src/ to PYTHONPATH
        src_dir = os.path.join(self.sandbox_dir, "src")
        existing_pythonpath = env.get("PYTHONPATH", "")
        paths_to_add = [self.sandbox_dir]
        if os.path.isdir(src_dir):
            paths_to_add.append(src_dir)
        if existing_pythonpath:
            paths_to_add.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(paths_to_add)

        start_time = time.time()
        timed_out = False
        raw_output = ""
        return_code = 0

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.sandbox_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            raw_output = proc.stdout + "\n" + proc.stderr
            return_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            raw_output = (exc.stdout or "") + "\n" + (exc.stderr or "") + f"\nTimed out after {self.timeout_seconds} seconds."
            return_code = -1
        except Exception as exc:
            raw_output = f"Execution error: {exc}"
            return_code = -1

        duration = time.time() - start_time
        return self._parse_pytest_output(raw_output, duration, return_code, timed_out)

    def _parse_pytest_output(self, output: str, duration: float, return_code: int, timed_out: bool) -> TestResult:
        test_cases: List[TestCaseStatus] = []
        passed_test_ids: Set[str] = set()
        failed_test_ids: Set[str] = set()

        # Regex for verbose pytest lines:
        # tests/test_billing.py::test_discount_basic PASSED [ 50%]
        # tests/test_billing.py::test_discount_negative FAILED [100%]
        pattern = re.compile(r"^([\w/\\._-]+::[\w_\[\]-]+)\s+(PASSED|FAILED|ERROR|SKIPPED)", re.MULTILINE)
        
        for match in pattern.finditer(output):
            nodeid = match.group(1).replace("\\", "/")
            raw_status = match.group(2).lower()
            name = nodeid.split("::")[-1]
            
            tc = TestCaseStatus(
                nodeid=nodeid,
                name=name,
                status=raw_status,
            )
            test_cases.append(tc)
            
            if raw_status == "passed":
                passed_test_ids.add(nodeid)
            elif raw_status in {"failed", "error"}:
                failed_test_ids.add(nodeid)

        # Summary line fallback if verbose lines couldn't be parsed
        # e.g., === 5 passed, 1 failed in 0.23s ===
        passed_count = len(passed_test_ids)
        failed_count = len(failed_test_ids)
        skipped_count = sum(1 for tc in test_cases if tc.status == "skipped")
        error_count = sum(1 for tc in test_cases if tc.status == "error")

        if not test_cases:
            # Parse summary line
            m_pass = re.search(r'(\d+)\s+passed', output)
            m_fail = re.search(r'(\d+)\s+failed', output)
            m_err = re.search(r'(\d+)\s+errors?', output)
            m_skip = re.search(r'(\d+)\s+skipped', output)

            if m_pass:
                passed_count = int(m_pass.group(1))
            if m_fail:
                failed_count = int(m_fail.group(1))
            if m_err:
                error_count = int(m_err.group(1))
            if m_skip:
                skipped_count = int(m_skip.group(1))

        total_tests = passed_count + failed_count + error_count + skipped_count
        no_tests = total_tests == 0
        overall_passed = (return_code == 0) and not no_tests and (failed_count == 0) and (error_count == 0) and not timed_out

        # Extract failure tracebacks
        failures_section = ""
        if "=== FAILURES ===" in output:
            parts = output.split("=== FAILURES ===")
            if len(parts) > 1:
                failures_section = parts[1].split("=== short test summary info ===")[0]

        return TestResult(
            passed=overall_passed,
            total_tests=total_tests,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            error_count=error_count,
            duration=duration,
            test_cases=test_cases,
            passed_test_ids=passed_test_ids,
            failed_test_ids=failed_test_ids,
            raw_output=output,
            timed_out=timed_out,
            return_code=return_code,
            no_tests=no_tests,
        )
