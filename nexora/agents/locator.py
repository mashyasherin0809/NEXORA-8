"""
Locator Agent for NEXORA-8.
Specializes in AST indexing, code map construction, and locating target files.
"""

from typing import List, Optional
from nexora.agents.base import BaseAgent, AgentStatus
from nexora.analyzer.repo_indexer import CodebaseIndexer, RepoIndex
from nexora.analyzer.retrieval import RelevanceLocator, RetrievedCandidate


class LocatorAgent(BaseAgent):
    """Pinpoints relevant files, classes, and functions from an unseen codebase."""

    def __init__(self):
        super().__init__(name="Locator", role_description="Maps AST repository structure and pinpoints relevant files")

    def run(self, repo_dir: str, task_description: str) -> tuple[RepoIndex, List[RetrievedCandidate]]:
        self.set_status(AgentStatus.WORKING, f"Indexing repository at {repo_dir}...")
        
        indexer = CodebaseIndexer(repo_dir)
        index = indexer.index()
        
        self.log(
            f"AST Index complete: {index.total_files} files, {index.total_lines} lines, "
            f"{index.total_symbols} symbols, {index.total_tests} test functions."
        )

        locator = RelevanceLocator(index)
        candidates = locator.locate_targets(task_description, top_k=5)

        if candidates:
            top_paths = [c.relative_path for c in candidates]
            self.log(f"Located {len(candidates)} candidate files: {', '.join(top_paths)}")
        else:
            self.log("No specific symbol matches found; using repository file list.")

        self.set_status(AgentStatus.COMPLETED, "Target discovery completed successfully.", data={
            "total_files": index.total_files,
            "candidates": [c.relative_path for c in candidates],
        })

        return index, candidates
