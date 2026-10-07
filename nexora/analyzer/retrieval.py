"""
Target File and Symbol Retrieval Locator for NEXORA-8.
Identifies relevant source and test files for any given task description.
"""

import math
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from nexora.analyzer.repo_indexer import RepoIndex, FileIndex, SymbolInfo


@dataclass
class RetrievedCandidate:
    relative_path: str
    score: float
    matched_symbols: List[str]
    matched_terms: List[str]
    is_test_file: bool
    snippet: str


class RelevanceLocator:
    """Ranks codebase files and symbols against a task / bug description."""

    def __init__(self, index: RepoIndex):
        self.index = index

    def locate_targets(self, task_description: str, top_k: int = 5) -> List[RetrievedCandidate]:
        """Find the top-K files and symbols most relevant to the task description."""
        query_terms = self._tokenize(task_description)
        if not query_terms:
            return []

        candidates: List[RetrievedCandidate] = []

        # Find direct symbol mentions
        symbol_mentions: Set[str] = set()
        for sym_name in self.index.symbol_table.keys():
            short_name = sym_name.split(".")[-1]
            if re.search(r'\b' + re.escape(short_name) + r'\b', task_description, re.IGNORECASE):
                symbol_mentions.add(sym_name)

        for rel_path, file_idx in self.index.files.items():
            if file_idx.parse_error:
                continue

            score = 0.0
            matched_syms: List[str] = []
            matched_terms: List[str] = []

            # 1. Path name match
            path_terms = self._tokenize(rel_path)
            path_overlap = set(path_terms).intersection(query_terms)
            if path_overlap:
                score += len(path_overlap) * 5.0
                matched_terms.extend(list(path_overlap))

            # 2. Symbol matches in this file
            for sym in file_idx.symbols:
                short_name = sym.name.split(".")[-1]
                if sym.name in symbol_mentions or short_name.lower() in query_terms:
                    score += 15.0
                    matched_syms.append(sym.name)

                # Docstring match
                if sym.docstring:
                    doc_terms = self._tokenize(sym.docstring)
                    doc_overlap = set(doc_terms).intersection(query_terms)
                    score += len(doc_overlap) * 2.0
                    matched_terms.extend(list(doc_overlap))

            # 3. Import & call matches
            for imp in file_idx.imports:
                imp_terms = self._tokenize(imp)
                imp_overlap = set(imp_terms).intersection(query_terms)
                score += len(imp_overlap) * 1.5

            # 4. Read file content for lexical matching
            try:
                with open(file_idx.file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                content_terms = self._tokenize(content)
                term_counts = {}
                for t in content_terms:
                    term_counts[t] = term_counts.get(t, 0) + 1

                for qt in query_terms:
                    if qt in term_counts:
                        # TF-IDF style weight
                        tf = 1 + math.log(term_counts[qt])
                        score += tf * 1.2
                        matched_terms.append(qt)

                # Generate brief snippet around best match
                snippet = self._extract_snippet(content, query_terms)
            except Exception:
                snippet = ""

            if score > 0:
                # Slight penalty for tests when looking for root cause, unless query mentions 'test'
                if file_idx.is_test_file and "test" not in task_description.lower():
                    score *= 0.7

                candidates.append(RetrievedCandidate(
                    relative_path=rel_path,
                    score=round(score, 2),
                    matched_symbols=sorted(list(set(matched_syms))),
                    matched_terms=sorted(list(set(matched_terms))),
                    is_test_file=file_idx.is_test_file,
                    snippet=snippet,
                ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        # Split camelCase and snake_case and whitespace
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
        s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        tokens = re.findall(r'[a-z0-9_]+', s2)
        # Filter short noise
        return [t for t in tokens if len(t) > 1 and t not in {"the", "and", "for", "with", "that", "this", "from"}]

    def _extract_snippet(self, content: str, query_terms: List[str], window: int = 10) -> str:
        lines = content.splitlines()
        best_line = 0
        max_matches = -1

        for i, line in enumerate(lines):
            line_terms = set(self._tokenize(line))
            matches = len(line_terms.intersection(query_terms))
            if matches > max_matches:
                max_matches = matches
                best_line = i

        start = max(0, best_line - window // 2)
        end = min(len(lines), start + window)
        return "\n".join(f"{idx+1:4d}: {lines[idx]}" for idx in range(start, end))
