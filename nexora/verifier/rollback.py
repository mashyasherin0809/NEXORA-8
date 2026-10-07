"""
Safe Rollback Manager for NEXORA-8.
"""

from typing import Dict, List, Optional
from nexora.verifier.sandbox import SandboxRunner


class RollbackManager:
    """Safely reverts sandboxed code when deterministic verification fails."""

    def __init__(self, sandbox: SandboxRunner):
        self.sandbox = sandbox
        self.rollback_history: List[str] = []

    def rollback(self, reason: str = "Verification failed"):
        """Restore sandbox to original baseline snapshot."""
        self.sandbox.rollback_all()
        self.rollback_history.append(reason)

    def revert_file(self, rel_path: str, reason: str = ""):
        """Revert a single file to its initial state."""
        self.sandbox.restore_file(rel_path)
        self.rollback_history.append(f"Reverted {rel_path}: {reason}")
