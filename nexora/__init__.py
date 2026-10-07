"""
NEXORA-8: Autonomous AI Software Engineering Agent
Built for HackNex 2026 (Problem Statement HNX26PSI09)

Combines probabilistic code intelligence with deterministic verification:
- AST-based codebase indexing and target retrieval
- Minimal patch synthesis
- Anti-hallucination & safety gatekeeping
- Sandboxed zero-regression pytest verification
- Autonomous regression test generation
- Live multi-agent monitoring telemetry
"""

__version__ = "1.0.0"
__author__ = "NEXORA-8 Team"

from nexora.config import Config
from nexora.analyzer.repo_indexer import CodebaseIndexer
from nexora.guard.hallucination_guard import HallucinationGuard
from nexora.verifier.sandbox import SandboxRunner
from nexora.verifier.test_runner import TestRunner
from nexora.verifier.regression_detector import RegressionDetector
from nexora.agents.orchestrator import OrchestratorAgent
from nexora.reporting.evidence import EvidenceReport

__all__ = [
    "Config",
    "CodebaseIndexer",
    "HallucinationGuard",
    "SandboxRunner",
    "TestRunner",
    "RegressionDetector",
    "OrchestratorAgent",
    "EvidenceReport",
]
