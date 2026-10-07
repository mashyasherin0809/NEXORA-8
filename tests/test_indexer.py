"""
Tests for NEXORA-8 Codebase AST Indexer.
"""

import os
import tempfile
import pytest
from nexora.analyzer.repo_indexer import CodebaseIndexer


def test_indexer_extracts_classes_functions_and_tests():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        src_file = os.path.join(tmpdir, "calculator.py")
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(
                '"""Calculator module."""\n'
                'import math\n\n'
                'class Calculator:\n'
                '    """A simple calculator."""\n'
                '    def add(self, a, b):\n'
                '        """Add two numbers."""\n'
                '        return a + b\n\n'
                'def standalone_func(x):\n'
                '    return math.sqrt(x)\n'
            )

        test_file = os.path.join(tmpdir, "test_calculator.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(
                'from calculator import Calculator\n\n'
                'def test_calc_add():\n'
                '    calc = Calculator()\n'
                '    assert calc.add(2, 3) == 5\n'
            )

        indexer = CodebaseIndexer(tmpdir)
        index = indexer.index()

        assert index.total_files == 2
        assert index.total_tests == 1
        assert "Calculator" in index.symbol_table
        assert "standalone_func" in index.symbol_table
        assert "math" in index.all_known_modules or "calculator" in index.all_known_modules
