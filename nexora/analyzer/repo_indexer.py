"""
AST-based Codebase Indexer for NEXORA-8.
Performs deterministic structural analysis of any Python repository.
"""

import ast
from dataclasses import dataclass, field, asdict
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any


@dataclass
class SymbolInfo:
    name: str
    kind: str  # 'function', 'class', 'method', 'constant'
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    args: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    parent_class: Optional[str] = None


@dataclass
class FileIndex:
    file_path: str
    relative_path: str
    total_lines: int
    imports: List[str] = field(default_factory=list)
    imported_names: Dict[str, str] = field(default_factory=dict)  # name -> module
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    symbols: List[SymbolInfo] = field(default_factory=list)
    is_test_file: bool = False
    test_functions: List[str] = field(default_factory=list)
    parse_error: Optional[str] = None


@dataclass
class RepoIndex:
    root_dir: str
    total_files: int
    total_lines: int
    total_symbols: int
    total_tests: int
    files: Dict[str, FileIndex] = field(default_factory=dict)  # rel_path -> FileIndex
    symbol_table: Dict[str, List[SymbolInfo]] = field(default_factory=dict)  # name -> [SymbolInfo]
    call_graph: Dict[str, List[str]] = field(default_factory=dict)  # caller -> [callees]
    all_known_modules: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "root_dir": self.root_dir,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_symbols": self.total_symbols,
            "total_tests": self.total_tests,
            "files": {
                rel: {
                    "relative_path": f.relative_path,
                    "total_lines": f.total_lines,
                    "imports": f.imports,
                    "classes": f.classes,
                    "functions": f.functions,
                    "is_test_file": f.is_test_file,
                    "test_functions": f.test_functions,
                    "symbols": [asdict(s) for s in f.symbols],
                    "parse_error": f.parse_error,
                }
                for rel, f in self.files.items()
            },
            "all_known_modules": sorted(list(self.all_known_modules)),
        }


class CodebaseIndexer:
    """Walks a Python repository and extracts full structural AST intelligence."""

    IGNORE_DIRS = {
        ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
        ".ruff_cache", ".tox", "node_modules", "dist", "build", ".egg-info",
        ".antigravity", ".gemini", "site-packages"
    }

    def __init__(self, root_dir: str):
        self.root_dir = os.path.abspath(root_dir)

    def index(self) -> RepoIndex:
        files: Dict[str, FileIndex] = {}
        symbol_table: Dict[str, List[SymbolInfo]] = {}
        call_graph: Dict[str, List[str]] = {}
        all_known_modules: Set[str] = set()

        total_lines = 0
        total_tests = 0
        total_symbols = 0

        for root, dirs, filenames in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.endswith(".egg-info")]

            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")

                    # Track module dotted name
                    mod_parts = Path(rel_path).with_suffix("").parts
                    if mod_parts and mod_parts[-1] == "__init__":
                        mod_name = ".".join(mod_parts[:-1])
                    else:
                        mod_name = ".".join(mod_parts)
                    if mod_name:
                        all_known_modules.add(mod_name)
                        all_known_modules.add(mod_name.split(".")[0])

                    file_index = self._index_file(full_path, rel_path)
                    files[rel_path] = file_index
                    total_lines += file_index.total_lines
                    total_tests += len(file_index.test_functions)
                    total_symbols += len(file_index.symbols)

                    for sym in file_index.symbols:
                        symbol_table.setdefault(sym.name, []).append(sym)
                        caller_key = f"{rel_path}::{sym.name}"
                        call_graph[caller_key] = sym.calls

        return RepoIndex(
            root_dir=self.root_dir,
            total_files=len(files),
            total_lines=total_lines,
            total_symbols=total_symbols,
            total_tests=total_tests,
            files=files,
            symbol_table=symbol_table,
            call_graph=call_graph,
            all_known_modules=all_known_modules,
        )

    def _index_file(self, full_path: str, rel_path: str) -> FileIndex:
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return FileIndex(
                file_path=full_path,
                relative_path=rel_path,
                total_lines=0,
                parse_error=f"Could not read file: {e}"
            )

        lines = content.splitlines()
        total_lines = len(lines)
        is_test_file = "test" in os.path.basename(rel_path).lower() or "/tests/" in f"/{rel_path}/"

        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError as e:
            return FileIndex(
                file_path=full_path,
                relative_path=rel_path,
                total_lines=total_lines,
                is_test_file=is_test_file,
                parse_error=f"SyntaxError on line {e.lineno}: {e.msg}"
            )

        imports: List[str] = []
        imported_names: Dict[str, str] = {}
        classes: List[str] = []
        functions: List[str] = []
        symbols: List[SymbolInfo] = []
        test_functions: List[str] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    imported_names[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                imports.append(mod)
                for alias in node.names:
                    imported_names[alias.asname or alias.name] = f"{mod}.{alias.name}" if mod else alias.name
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                class_doc = ast.get_docstring(node)
                class_sym = SymbolInfo(
                    name=node.name,
                    kind="class",
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    docstring=class_doc,
                    decorators=[self._get_name(d) for d in node.decorator_list],
                )
                symbols.append(class_sym)

                # Class methods
                for class_node in node.body:
                    if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(class_node)
                        args = [a.arg for a in class_node.args.args]
                        calls = self._extract_calls(class_node)
                        m_sym = SymbolInfo(
                            name=f"{node.name}.{class_node.name}",
                            kind="method",
                            file_path=rel_path,
                            line_start=class_node.lineno,
                            line_end=getattr(class_node, "end_lineno", class_node.lineno),
                            docstring=method_doc,
                            args=args,
                            calls=calls,
                            decorators=[self._get_name(d) for d in class_node.decorator_list],
                            parent_class=node.name,
                        )
                        symbols.append(m_sym)
                        if class_node.name.startswith("test_"):
                            test_functions.append(f"{node.name}::{class_node.name}")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                fn_doc = ast.get_docstring(node)
                args = [a.arg for a in node.args.args]
                calls = self._extract_calls(node)
                fn_sym = SymbolInfo(
                    name=node.name,
                    kind="function",
                    file_path=rel_path,
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno),
                    docstring=fn_doc,
                    args=args,
                    calls=calls,
                    decorators=[self._get_name(d) for d in node.decorator_list],
                )
                symbols.append(fn_sym)
                if node.name.startswith("test_"):
                    test_functions.append(node.name)

        return FileIndex(
            file_path=full_path,
            relative_path=rel_path,
            total_lines=total_lines,
            imports=imports,
            imported_names=imported_names,
            classes=classes,
            functions=functions,
            symbols=symbols,
            is_test_file=is_test_file,
            test_functions=test_functions,
        )

    def _extract_calls(self, node: ast.AST) -> List[str]:
        calls: Set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = self._get_name(child.func)
                if name:
                    calls.add(name)
        return sorted(list(calls))

    def _get_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ""
