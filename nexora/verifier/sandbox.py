"""
Isolated Sandbox Environment for NEXORA-8.
Guarantees that all repairs, test executions, and experiments happen
inside an isolated temporary environment without polluting the original repository.
"""

import os
import shutil
import tempfile
from typing import Dict, Optional, Set


class SandboxRunner:
    """Manages an isolated workspace for applying patches and running tests."""

    def __init__(self, original_repo_dir: str, sandbox_base: Optional[str] = None):
        self.original_repo_dir = os.path.abspath(original_repo_dir)
        self.sandbox_base = sandbox_base
        self.sandbox_dir: Optional[str] = None
        self._initial_file_snapshots: Dict[str, str] = {}

    def setup(self) -> str:
        """Create the temporary copy of the repository."""
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            return self.sandbox_dir

        self.sandbox_dir = tempfile.mkdtemp(prefix="nexora_sandbox_", dir=self.sandbox_base)
        
        # Copy everything except heavy cache / VCS folders
        ignore_patterns = shutil.ignore_patterns(
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
            ".ruff_cache", "node_modules", "*.egg-info", ".antigravity", ".gemini"
        )
        
        for item in os.listdir(self.original_repo_dir):
            s = os.path.join(self.original_repo_dir, item)
            d = os.path.join(self.sandbox_dir, item)
            if item in {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".antigravity", ".gemini"}:
                continue
            if os.path.isdir(s):
                shutil.copytree(s, d, ignore=ignore_patterns, symlinks=False)
            else:
                shutil.copy2(s, d)

        return self.sandbox_dir

    def read_file(self, rel_path: str) -> str:
        """Read file from sandbox."""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox not initialized. Call setup() first.")
        full_path = os.path.join(self.sandbox_dir, rel_path)
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def write_file(self, rel_path: str, content: str) -> str:
        """Write modified content to sandbox file, saving snapshot for rollback."""
        if not self.sandbox_dir:
            raise RuntimeError("Sandbox not initialized. Call setup() first.")
        normalized = os.path.normpath(rel_path).replace("\\", "/")
        if normalized.startswith("../") or normalized == "..":
            raise ValueError(f"Unsafe path outside sandbox: {rel_path}")
        full_path = os.path.join(self.sandbox_dir, normalized)

        # Existing tests are evidence, not an edit surface. New generated test
        # files are allowed, but overwriting or deleting a repository test is not.
        is_test = normalized.startswith(("tests/", "test/")) or "/tests/" in normalized or "/test/" in normalized
        if is_test and os.path.exists(full_path) and normalized not in self._initial_file_snapshots:
            raise PermissionError(f"PROTECTED TEST FILE: existing test cannot be modified: {normalized}")
        
        # Save snapshot on first write
        if normalized not in self._initial_file_snapshots and os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                self._initial_file_snapshots[normalized] = f.read()

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return full_path

    def restore_file(self, rel_path: str):
        """Restore single file to initial snapshot."""
        if rel_path in self._initial_file_snapshots:
            self.write_file(rel_path, self._initial_file_snapshots[rel_path])

    def rollback_all(self):
        """Restore all modified files back to original snapshot."""
        for rel_path, content in self._initial_file_snapshots.items():
            full_path = os.path.join(self.sandbox_dir, rel_path)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

    def sync_back_to_original(self, modified_files: Set[str]):
        """Persist verified files back into original repository."""
        if not self.sandbox_dir:
            return
        for rel_path in modified_files:
            sandbox_file = os.path.join(self.sandbox_dir, rel_path)
            orig_file = os.path.join(self.original_repo_dir, rel_path)
            if os.path.exists(sandbox_file):
                os.makedirs(os.path.dirname(orig_file), exist_ok=True)
                shutil.copy2(sandbox_file, orig_file)

    def cleanup(self):
        """Clean up temporary sandbox directory."""
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            except Exception:
                pass
            self.sandbox_dir = None
