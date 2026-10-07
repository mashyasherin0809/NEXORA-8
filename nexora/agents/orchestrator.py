"""
Multi-Agent Orchestrator for NEXORA-8.
Supervises the complete self-healing, verification, and test generation lifecycle.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional, Set

from nexora.config import Config
from nexora.agents.base import BaseAgent, AgentEvent, AgentStatus
from nexora.agents.locator import LocatorAgent
from nexora.agents.planner import PlannerAgent, RepairPlan
from nexora.agents.patcher import PatcherAgent, GeneratedPatch
from nexora.agents.verifier_agent import VerifierAgent
from nexora.agents.test_gen_agent import TestGenAgent, GeneratedTestSuite
from nexora.analyzer.repo_indexer import RepoIndex
from nexora.guard.hallucination_guard import HallucinationGuard, GuardReport
from nexora.llm.client import LLMClient
from nexora.reporting.evidence import EvidenceReport
from nexora.verifier.rollback import RollbackManager
from nexora.verifier.sandbox import SandboxRunner
from nexora.verifier.test_runner import TestRunner, TestResult
from nexora.verifier.regression_detector import VerificationVerdict


@dataclass
class RepairSession:
    session_id: str
    task_description: str
    repo_path: str
    status: str  # "running", "success", "failed", "rolled_back"
    start_time: float
    end_time: Optional[float] = None
    attempts: int = 0
    max_attempts: int = 3
    plan: Optional[RepairPlan] = None
    patches: List[GeneratedPatch] = field(default_factory=list)
    guard_report: Optional[GuardReport] = None
    baseline_tests: Optional[TestResult] = None
    final_tests: Optional[TestResult] = None
    verification_verdict: Optional[VerificationVerdict] = None
    generated_tests: Optional[GeneratedTestSuite] = None
    evidence_report: Optional[EvidenceReport] = None
    events: List[AgentEvent] = field(default_factory=list)
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_description": self.task_description,
            "repo_path": self.repo_path,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "cost_usd": round(self.cost_usd, 4),
            "plan": self.plan.to_dict() if self.plan else None,
            "patches": [
                {
                    "file": p.file_path,
                    "search": p.search_block,
                    "replace": p.replace_block,
                    "explanation": p.explanation,
                    "diff": p.diff_text,
                    "success": p.success,
                }
                for p in self.patches
            ],
            "guard_report": self.guard_report.to_dict() if self.guard_report else None,
            "baseline_tests": self.baseline_tests.to_dict() if self.baseline_tests else None,
            "final_tests": self.final_tests.to_dict() if self.final_tests else None,
            "verification_verdict": self.verification_verdict.to_dict() if self.verification_verdict else None,
            "generated_tests": {
                "file_path": self.generated_tests.file_path,
                "test_code": self.generated_tests.test_code,
                "passed": self.generated_tests.passed,
                "count": self.generated_tests.test_count,
            } if self.generated_tests else None,
            "evidence_report": self.evidence_report.to_markdown() if self.evidence_report else None,
            "events": [e.to_dict() for e in self.events],
        }


class OrchestratorAgent(BaseAgent):
    """Coordinates multi-agent execution, deterministic validation gates, and telemetry streaming."""

    def __init__(self, config: Optional[Config] = None):
        super().__init__(name="Orchestrator", role_description="Coordinates overall lifecycle, safety gates, and retries")
        self.config = config or Config()
        self.llm_client = LLMClient(self.config)

        # Specialized Sub-Agents
        self.locator = LocatorAgent()
        self.planner = PlannerAgent(self.llm_client)
        self.patcher = PatcherAgent(
            self.llm_client,
            max_diff_lines=self.config.max_diff_lines,
            max_changed_files=getattr(self.config, "max_changed_files", 5),
            max_added_lines=getattr(self.config, "max_added_lines", 80),
        )
        self.verifier = VerifierAgent()
        self.test_gen = TestGenAgent(self.llm_client)

        # Forward all sub-agent events
        for ag in [self.locator, self.planner, self.patcher, self.verifier, self.test_gen]:
            ag.add_event_listener(self._handle_subagent_event)

        self.current_session: Optional[RepairSession] = None

    def _handle_subagent_event(self, event: AgentEvent):
        if self.current_session:
            self.current_session.events.append(event)
        self._emit(event)

    def execute_task(
        self,
        repo_path: str,
        task_description: str,
        apply_to_original: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> RepairSession:
        session_id = f"ses_{int(time.time())}"
        session = RepairSession(
            session_id=session_id,
            task_description=task_description,
            repo_path=repo_path,
            status="running",
            start_time=time.time(),
            max_attempts=self.config.max_repair_attempts,
        )
        self.current_session = session

        self.set_status(AgentStatus.WORKING, f"Starting autonomous repair session {session_id} on {repo_path}")
        if progress_callback:
            progress_callback("Setting up sandbox environment...", 0.1)

        # 1. Setup Isolated Sandbox
        sandbox = SandboxRunner(repo_path, sandbox_base=self.config.sandbox_base_dir)
        sandbox_dir = sandbox.setup()
        rollback_mgr = RollbackManager(sandbox)
        test_runner = TestRunner(sandbox_dir, timeout_seconds=self.config.test_timeout_seconds)

        try:
            # 2. Baseline Test Execution
            if progress_callback:
                progress_callback("Running baseline test suite...", 0.2)
            baseline_result = self.verifier.run_baseline(test_runner)
            session.baseline_tests = baseline_result

            # 3. Structural AST Analysis & Target Discovery
            if progress_callback:
                progress_callback("Indexing AST codebase...", 0.35)
            repo_index, candidates = self.locator.run(sandbox_dir, task_description)
            self.log(
                "Retrieval evidence: " + "; ".join(
                    f"{c.relative_path} score={c.score} terms={','.join(c.matched_terms[:5])}"
                    for c in candidates[:5]
                )
            )
            guard = HallucinationGuard(known_repo_modules=repo_index.all_known_modules, max_diff_lines=self.config.max_diff_lines)

            # 4. Planning Phase
            if progress_callback:
                progress_callback("Formulating repair plan...", 0.5)
            plan = self.planner.plan(
                task_description=task_description,
                candidates=candidates,
                failing_tests_summary=baseline_result.raw_output if not baseline_result.passed else None,
            )
            session.plan = plan

            # 5. Iterative Repair Loop
            verified = False
            feedback: Optional[str] = None
            modified_files: Set[str] = set()

            for attempt in range(1, self.config.max_repair_attempts + 1):
                session.attempts = attempt
                if progress_callback:
                    progress_callback(f"Synthesizing patch (Attempt {attempt}/{self.config.max_repair_attempts})...", 0.6 + (attempt * 0.08))

                # Revert any previous failed attempt in sandbox
                if attempt > 1:
                    rollback_mgr.rollback(reason=f"Retrying after attempt {attempt-1} failure")

                # Generate patch
                patches = self.patcher.patch(
                    sandbox=sandbox,
                    plan=plan,
                    attempt_number=attempt,
                    feedback=feedback,
                )
                session.patches = patches

                if not any(p.success for p in patches):
                    feedback = "Patch failed to apply to the original code. Make sure search block matches lines exactly."
                    continue

                # Safety & Hallucination Guard Gate
                guard_passed = True
                for p in patches:
                    if p.success:
                        modified_files.add(p.file_path)
                        orig_code = sandbox._initial_file_snapshots.get(p.file_path, "")
                        mod_code = sandbox.read_file(p.file_path)
                        guard_report = guard.validate_patch(orig_code, mod_code, file_path=p.file_path)
                        session.guard_report = guard_report

                        if not guard_report.passed:
                            guard_passed = False
                            feedback = (
                                f"Safety Guard rejected patch on {p.file_path}: "
                                f"{'; '.join(f.message for f in guard_report.findings)}"
                            )
                            self.log(f"Safety Guard Rejection: {feedback}")
                            break

                if not guard_passed:
                    continue

                # Deterministic Sandbox Pytest Verification Gate
                post_test_result, verdict = self.verifier.verify_patch(test_runner, baseline_result)
                session.final_tests = post_test_result
                session.verification_verdict = verdict

                if verdict.has_regressions:
                    feedback = (
                        f"REGRESSION DETECTED! Previously passing test(s) failed after patch: "
                        f"{', '.join(verdict.regressions)}.\nTraceback snippet:\n{post_test_result.raw_output[:600]}"
                    )
                    self.log(feedback)
                    continue

                if verdict.is_verified or post_test_result.passed:
                    verified = True
                    self.log(f"Deterministic verification SUCCESS on Attempt {attempt}!")
                    break
                else:
                    feedback = f"Test suite still failing:\n{post_test_result.raw_output[:500]}"

            # 6. Post-Verification Phase (Test Generation & Finalization)
            if verified:
                if progress_callback:
                    progress_callback("Generating new acceptance tests...", 0.9)
                gen_suite = self.test_gen.generate_and_verify(
                    sandbox=sandbox,
                    runner=test_runner,
                    task_description=task_description,
                    plan=plan,
                    modified_files=list(modified_files),
                )
                session.generated_tests = gen_suite

                # If requested, sync verified changes back to original repo
                if apply_to_original:
                    sandbox.sync_back_to_original(modified_files)
                    self.log(f"Synchronized verified changes back to original repository ({len(modified_files)} files).")

                session.status = "success"
                self.set_status(AgentStatus.COMPLETED, "Repair session completed successfully with zero regressions!")
            else:
                rollback_mgr.rollback(reason="Max attempts reached without verification")
                session.status = "rolled_back"
                self.set_status(AgentStatus.FAILED, "Verification could not be established. Changes rolled back.")

            # 7. Generate Evidence Report
            evidence = EvidenceReport.create(session)
            session.evidence_report = evidence

        finally:
            sandbox.cleanup()
            session.end_time = time.time()

        if progress_callback:
            progress_callback("Done!", 1.0)

        return session
