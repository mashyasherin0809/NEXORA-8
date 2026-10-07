"""
Code Quality and Complexity Metrics for NEXORA-8.
"""

import ast
import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class CodeMetrics:
    total_lines: int
    blank_lines: int
    comment_lines: int
    code_lines: int
    complexity: int  # Cyclomatic branches (if, elif, for, while, except, and, or)
    functions_count: int
    classes_count: int
    maintainability_index: float

    @classmethod
    def analyze_source(cls, source_code: str) -> "CodeMetrics":
        lines = source_code.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        comment_lines = sum(1 for l in lines if l.strip().startswith("#"))
        code_lines = total_lines - blank_lines - comment_lines

        complexity = 1  # Base complexity
        functions_count = 0
        classes_count = 0

        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions_count += 1
                elif isinstance(node, ast.ClassDef):
                    classes_count += 1
        except Exception:
            # Fallback regex complexity
            complexity += len(re.findall(r'\b(if|elif|while|for|except|and|or)\b', source_code))

        # Simplified maintainability index formula: 171 - 5.2 * ln(Halstead Vol) - 0.23 * (Cyclomatic) - 16.2 * ln(LOC)
        # Scaled to 0-100
        mi = max(0.0, min(100.0, 100.0 - (complexity * 2.5) - (code_lines * 0.1)))

        return cls(
            total_lines=total_lines,
            blank_lines=blank_lines,
            comment_lines=comment_lines,
            code_lines=code_lines,
            complexity=complexity,
            functions_count=functions_count,
            classes_count=classes_count,
            maintainability_index=round(mi, 1),
        )
