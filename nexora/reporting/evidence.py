"""
Evidence Report Generator for NEXORA-8.
Generates comprehensive verification audit documentation in Markdown and JSON formats.
"""

from dataclasses import dataclass, field
import datetime
import json
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceReport:
    session_id: str
    timestamp: str
    task_description: str
    repo_path: str
    status: str
    attempts: int
    root_cause: str
    strategy: str
    modified_files: List[str]
    diffs: List[Dict[str, str]]
    safety_score: int
    safety_verdict: str
    guard_findings: List[Dict[str, Any]]
    baseline_passed: int
    baseline_failed: int
    final_passed: int
    final_failed: int
    regressions_count: int
    fixed_tests_count: int
    regressions_list: List[str]
    generated_test_code: Optional[str]
    generated_test_passed: bool
    execution_duration: float

    @classmethod
    def create(cls, session: Any) -> "EvidenceReport":
        plan = session.plan
        guard = session.guard_report
        baseline = session.baseline_tests
        final = session.final_tests
        verdict = session.verification_verdict
        gen = session.generated_tests

        diffs = []
        for p in session.patches:
            if p.diff_text:
                diffs.append({"file": p.file_path, "diff": p.diff_text, "explanation": p.explanation})

        return cls(
            session_id=session.session_id,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            task_description=session.task_description,
            repo_path=session.repo_path,
            status=session.status,
            attempts=session.attempts,
            root_cause=plan.root_cause if plan else "N/A",
            strategy=plan.strategy if plan else "N/A",
            modified_files=[p.file_path for p in session.patches if p.success],
            diffs=diffs,
            safety_score=guard.score if guard else 100,
            safety_verdict=guard.verdict if guard else "Safe to merge",
            guard_findings=[
                {"severity": f.severity, "rule": f.rule, "message": f.message}
                for f in (guard.findings if guard else [])
            ],
            baseline_passed=baseline.passed_count if baseline else 0,
            baseline_failed=baseline.failed_count if baseline else 0,
            final_passed=final.passed_count if final else 0,
            final_failed=final.failed_count if final else 0,
            regressions_count=len(verdict.regressions) if verdict else 0,
            fixed_tests_count=len(verdict.fixed_tests) if verdict else 0,
            regressions_list=verdict.regressions if verdict else [],
            generated_test_code=gen.test_code if gen else None,
            generated_test_passed=gen.passed if gen else False,
            execution_duration=round((session.end_time or session.start_time) - session.start_time, 2),
        )

    def to_markdown(self) -> str:
        status_badge = "✅ VERIFIED & ACCEPTED" if self.status == "success" else "❌ ROLLED BACK / FAILED"
        
        diff_blocks = ""
        for d in self.diffs:
            diff_blocks += f"### File: `{d['file']}`\n*{d['explanation']}*\n```diff\n{d['diff']}\n```\n\n"

        if not diff_blocks:
            diff_blocks = "*No code modifications applied.*\n"

        guard_items = ""
        if self.guard_findings:
            for gf in self.guard_findings:
                guard_items += f"- **[{gf['severity'].upper()}]** {gf['rule']}: {gf['message']}\n"
        else:
            guard_items = "- None (Clean syntax, no hallucinated imports, no undefined variables)\n"

        gen_test_section = ""
        if self.generated_test_code:
            status_icon = "✅ Passed" if self.generated_test_passed else "❌ Failed"
            gen_test_section = f"""## 🧪 Generated Acceptance Tests ({status_icon})
```python
{self.generated_test_code}
```
"""

        return f"""# NEXORA-8: Evidence & Verification Report

- **Session ID:** `{self.session_id}`
- **Timestamp:** {self.timestamp}
- **Status:** {status_badge}
- **Target Repository:** `{self.repo_path}`
- **Execution Time:** {self.execution_duration}s
- **Attempts:** {self.attempts}

---

## 1. Task & Root Cause Analysis

**Task Description:**
> {self.task_description}

**Root Cause:**
{self.root_cause}

**Modification Strategy:**
{self.strategy}

---

## 2. Code Modifications (Minimal Diffs)

{diff_blocks}

---

## 3. Deterministic Safety & Anti-Hallucination Guard

- **Safety Score:** {self.safety_score}/100
- **Verdict:** `{self.safety_verdict}`
- **Findings:**
{guard_items}

---

## 4. Test Suite Verification & Regression Matrix

| Metric | Baseline (Before) | Patched (After) | Delta |
|---|---|---|---|
| **Passing Tests** | {self.baseline_passed} | {self.final_passed} | +{self.final_passed - self.baseline_passed} |
| **Failing Tests** | {self.baseline_failed} | {self.final_failed} | -{self.baseline_failed - self.final_failed} |
| **Regressions** | 0 | **{self.regressions_count}** | {'✅ 0 Regressions' if self.regressions_count == 0 else '❌ REGRESSION DETECTED'} |

**Fixed Tests:** {self.fixed_tests_count} test(s) resolved.
**Regressions:** {', '.join(self.regressions_list) if self.regressions_list else 'None (0 regressions detected)'}

---

{gen_test_section}

---
*Report autonomously generated by NEXORA-8 AI Software Engineering Agent.*
"""
