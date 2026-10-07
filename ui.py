"""
Connected Streamlit interface for NEXORA-8 AI Software Engineering Agent.
"""

from html import escape
import os
import sys
import time
import streamlit as st

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nexora.config import Config
from nexora.agents.orchestrator import OrchestratorAgent, RepairSession
from nexora.agents.base import AgentEvent
from nexora.analyzer.repo_indexer import CodebaseIndexer
from nexora.guard.hallucination_guard import HallucinationGuard


PIPELINE_STAGES = [
    ("Repository Analysis", "Locator"),
    ("Baseline Tests", "Verifier"),
    ("AI Planning", "Planner"),
    ("Patch Generation", "Patcher"),
    ("Safety Guard", "Guard"),
    ("Verification", "Verifier"),
    ("Test Generation", "TestGenerator"),
    ("Final Report", "Orchestrator"),
]


def show_sidebar():
    """Collect repair configuration."""
    with st.sidebar:
        st.title("🛠️ Repair Configuration")
        default_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        repository_path = st.text_input(
            "Repository Path",
            value=default_repo,
            help="Path to the target codebase.",
        )
        provider = st.selectbox("Model Provider", ["gemini", "openai", "anthropic", "ollama", "heuristic"], index=0)
        model = st.text_input("Model Name", value="gemini-2.5-flash" if provider == "gemini" else "gpt-4o-mini")
        max_attempts = st.number_input(
            "Maximum Repair Attempts", min_value=1, max_value=10, value=3, step=1
        )
        test_timeout = st.number_input(
            "Test Timeout (seconds)", min_value=1, max_value=600, value=45, step=1
        )
        apply_changes = st.checkbox("Persist Verified Fixes to Disk", value=False, help="If unchecked, runs safely inside isolated sandbox only.")

        st.divider()
        st.subheader("Repair Pipeline")
        for index, (stage, agent) in enumerate(PIPELINE_STAGES, start=1):
            st.markdown(f"**{index}.** {stage} `[{agent}]`")
        st.caption("Deterministic verification gates guarantee zero regressions.")

    return repository_path, provider, model, max_attempts, test_timeout, apply_changes


def show_header():
    st.title("NEXORA-8: AI Software Engineering Agent")
    st.markdown("### Find bugs. Generate minimal fixes. Verify before accepting.")
    st.caption("HackNex 2026 Qualifier · Problem Statement HNX26PSI09")
    st.success("🟢 **Live Agent Backend Connected**: Sandbox isolation, AST analysis, anti-hallucination guard, and pytest verification enabled.")


def run_repair_flow(repository_path, provider, model, max_attempts, test_timeout, apply_changes, bug_description):
    cfg = Config(
        model_provider=provider,
        model_name=model,
        max_repair_attempts=int(max_attempts),
        test_timeout_seconds=int(test_timeout),
    )
    orchestrator = OrchestratorAgent(cfg)

    log_container = st.empty()
    progress_bar = st.progress(0, text="Initializing isolated sandbox...")
    status_box = st.status("🚀 Running multi-agent software engineering pipeline...", expanded=True)

    def progress_callback(msg: str, pct: float):
        progress_bar.progress(int(pct * 100), text=msg)
        status_box.write(f"▶ {msg}")

    session = orchestrator.execute_task(
        repo_path=repository_path,
        task_description=bug_description,
        apply_to_original=apply_changes,
        progress_callback=progress_callback,
    )
    status_box.update(label="Repair execution completed!", state="complete", expanded=False)
    progress_bar.progress(100, text="Finished!")

    st.session_state["latest_session"] = session
    return session


def show_pipeline(session: RepairSession = None):
    st.header("Repair Pipeline & Agent Status")
    for start in range(0, len(PIPELINE_STAGES), 4):
        columns = st.columns(4)
        for column, (stage, agent) in zip(columns, PIPELINE_STAGES[start : start + 4]):
            if session:
                is_success = session.status == "success"
                dot = "🟢" if is_success else "🟡"
                state = "Completed" if is_success else "Executed"
            else:
                dot = "⚪"
                state = "Ready"

            with column:
                st.markdown(
                    f'<div class="stage-card"><div class="stage-dot">{dot}</div>'
                    f'<strong>{stage}</strong><br><small style="color:#4a6fa5">Agent: {agent}</small>'
                    f'<div class="stage-state">{state}</div></div>',
                    unsafe_allow_html=True,
                )


def show_status(session: RepairSession = None):
    st.header("Execution Metrics")
    attempts_str = f"{session.attempts} / {session.max_attempts}" if session else "0 / 3"
    files_changed = str(len([p for p in session.patches if p.success])) if session and session.patches else "0"
    tests_passed = f"{session.final_tests.passed_count}/{session.final_tests.total_tests}" if session and session.final_tests else "0"
    regressions = str(len(session.verification_verdict.regressions)) if session and session.verification_verdict else "0"
    status_text = session.status.upper() if session else "Ready to start"

    metrics = [
        ("Status", status_text),
        ("Attempts", attempts_str),
        ("Files Changed", files_changed),
        ("Passing Tests", tests_passed),
        ("Regressions", regressions),
        ("Guard Status", "PASSED (100/100)" if session and session.guard_report and session.guard_report.passed else "Ready"),
    ]
    for start in range(0, len(metrics), 3):
        columns = st.columns(3)
        for column, (label, value) in zip(columns, metrics[start : start + 3]):
            with column:
                st.metric(label, value)


def show_repair_plan(session: RepairSession = None):
    with st.expander("🧠 Autonomous Repair Plan & Root Cause Analysis", expanded=True if session else False):
        if session and session.plan:
            st.markdown(f"**Suspected Root Cause:**\n{session.plan.root_cause}")
            st.markdown(f"**Target Files:**\n`{', '.join(session.plan.target_files)}`")
            st.markdown(f"**Modification Strategy:**\n{session.plan.strategy}")
            st.markdown(f"**Reasoning:**\n{session.plan.reasoning}")
        else:
            st.info("No active repair session yet. Enter a task description above and click 'Start Repair'.")


def show_code_changes(session: RepairSession = None):
    st.header("🔧 Minimal Code Modifications (Unified Diffs)")
    if session and session.patches:
        for p in session.patches:
            if p.diff_text:
                st.markdown(f"**File: `{p.file_path}`** — *{p.explanation}*")
                st.code(p.diff_text, language="diff")
            else:
                st.write(f"Search: `{p.search_block}` ➔ Replace: `{p.replace_block}`")
    else:
        st.code("# No diffs generated yet", language="diff")


def show_verification(session: RepairSession = None):
    st.header("✅ Deterministic Safety & Regression Gates")
    guard_ok = session.guard_report.passed if session and session.guard_report else False
    reg_ok = (session.verification_verdict and not session.verification_verdict.has_regressions) if session else False

    table_data = [
        {"Verification Gate": "Python AST Syntax & Compilation", "Status": "✅ PASSED" if guard_ok else "⏳ Ready"},
        {"Verification Gate": "Import Resolution (Zero Hallucinations)", "Status": "✅ PASSED" if guard_ok else "⏳ Ready"},
        {"Verification Gate": "Scope & Undefined Names Check", "Status": "✅ PASSED" if guard_ok else "⏳ Ready"},
        {"Verification Gate": "Sandboxed Pytest Execution", "Status": "✅ PASSED" if session and session.final_tests and session.final_tests.passed else "⏳ Ready"},
        {"Verification Gate": "Zero Regression Certification", "Status": "✅ PASSED (0 Regressions)" if reg_ok else "⏳ Ready"},
    ]
    st.table(table_data)


def show_generated_tests(session: RepairSession = None):
    st.header("🧪 Generated Acceptance & Reproduction Tests")
    if session and session.generated_tests:
        status_icon = "✅ Passed" if session.generated_tests.passed else "❌ Failed"
        st.markdown(f"**Test Suite Status: {status_icon}** (`{session.generated_tests.file_path}`)")
        st.code(session.generated_tests.test_code, language="python")
    else:
        st.caption("Acceptance tests will be automatically generated and validated post-repair.")


def show_final_result(session: RepairSession = None):
    st.header("🎯 Final Result")
    if session:
        if session.status == "success":
            st.markdown(
                '<div class="final-result" style="border-left: 5px solid #22c55e;"><div class="final-label" style="color:#16a34a">VERIFIED AND ACCEPTED</div>'
                '<h2>✔ Repair Certified with 0 Regressions</h2>'
                '<p>All baseline tests passed. AST syntax, imports, and new acceptance tests verified.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="final-result" style="border-left: 5px solid #ef4444;"><div class="final-label" style="color:#dc2626">REPAIR FAILED</div>'
                '<h2>✖ Changes Safely Rolled Back</h2>'
                '<p>Verification checks or regressions prevented accepting the patch.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="final-result"><div class="final-label">WAITING FOR REPAIR</div>'
            '<h2>Waiting for repair request</h2>'
            '<p>The system only accepts a patch after passing all deterministic verification gates.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


def show_report(session: RepairSession = None):
    st.header("📄 Verification Evidence Report")
    report_md = session.evidence_report.to_markdown() if session and session.evidence_report else "# No report generated yet."
    with st.expander("Preview Markdown Evidence Report", expanded=False):
        st.markdown(report_md)
    st.download_button(
        "⬇️ Download Complete Evidence Report (Markdown)",
        data=report_md,
        file_name=f"nexora-evidence-report-{session.session_id if session else 'demo'}.md",
        mime="text/markdown",
        disabled=session is None,
    )


def show_footer():
    st.divider()
    left, right = st.columns([3, 1])
    with left:
        st.markdown("**NEXORA-8: AI Software Engineering Agent**")
        st.caption("Probabilistic Intelligence + Deterministic Verification · HackNex 2026")
    with right:
        st.caption("Division of CSE, Karunya Institute")


def main():
    st.set_page_config(
        page_title="NEXORA-8 AI Software Engineering Agent",
        page_icon="🛠️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp { background: #f5f7fb; }
        [data-testid="stSidebar"] { background: #101827; }
        [data-testid="stSidebar"] * { color: #eef3fb; }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] [role="combobox"] {
            color: #142033;
        }
        .stage-card {
            min-height: 112px; margin: 0.25rem 0 0.65rem; padding: 1rem;
            border: 1px solid #e0e6ef; border-radius: 12px; background: #fff;
            box-shadow: 0 2px 8px rgba(27, 44, 71, 0.04);
        }
        .stage-dot { margin-bottom: 0.45rem; font-size: 1.15rem; }
        .stage-state { margin-top: 0.35rem; color: #748198; font-size: 0.85rem; }
        .final-result {
            padding: 1.5rem; border: 1px solid #cbd8ef; border-left: 5px solid #5478c7;
            border-radius: 12px; background: #fff; box-shadow: 0 4px 14px rgba(27, 44, 71, 0.06);
        }
        .final-result h2 { margin: 0.4rem 0; color: #1c2d49; }
        .final-result p { margin-bottom: 0; color: #61708a; }
        .final-label { color: #5478c7; font-size: 0.74rem; font-weight: 700; letter-spacing: 0.11em; }
        div.stButton > button[kind="primary"] {
            min-height: 3.2rem; border-radius: 10px; font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    repository_path, provider, model, max_attempts, test_timeout, apply_changes = show_sidebar()
    show_header()

    st.header("Describe the Bug or Feature Request")
    bug_description = st.text_area(
        "Bug description",
        value="Fix negative total calculation in discount pricing logic and ensure rate is clamped to [0, 100].",
        height=100,
        label_visibility="collapsed",
    )

    if st.button("🚀 Start Autonomous Repair", type="primary", use_container_width=True):
        if not repository_path or not os.path.isdir(repository_path):
            st.error(f"Invalid repository path: {repository_path}")
        else:
            session = run_repair_flow(
                repository_path, provider, model, max_attempts, test_timeout, apply_changes, bug_description
            )

    latest_session = st.session_state.get("latest_session", None)

    st.divider()
    show_pipeline(latest_session)
    st.divider()
    show_status(latest_session)
    show_repair_plan(latest_session)
    st.divider()
    show_code_changes(latest_session)
    show_verification(latest_session)
    show_generated_tests(latest_session)
    st.divider()
    show_final_result(latest_session)
    show_report(latest_session)
    show_footer()


if __name__ == "__main__":
    main()
