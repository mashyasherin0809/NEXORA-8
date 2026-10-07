# RepoPilot Pitch Script

RepoPilot is an AI Software Engineer that does not just write code. It proves the fix is safe.

A developer gives RepoPilot a repository and a task. RepoPilot clones or copies it into an isolated workspace, understands the structure, ranks the relevant files and symbols, captures a baseline, applies a minimal patch, and runs the real build and test commands.

Our first differentiator is the **Regression Guardian**. It compares individual test identities before and after the change. A pre-existing failure is recorded separately; a test that was green and becomes red blocks the run immediately.

Our second differentiator is the **Hallucination Guard**. It checks imports, symbols, dependencies, syntax, compilation, protected test paths, and diff budgets. The LLM proposes; deterministic gates approve.

Our third differentiator is the **Self-Repair Loop**. When a patch fails, RepoPilot rolls it back, feeds the exact guard or test evidence back to the Code Agent, and retries within a strict attempt limit. A green test run is not enough unless the evidence explains why the change is safe.

The result is a verified verdict, a plain-English root cause, the ranked search evidence, the generated acceptance test, and a reproducible artifact bundle. RepoPilot turns AI coding from suggestion into accountable engineering.
