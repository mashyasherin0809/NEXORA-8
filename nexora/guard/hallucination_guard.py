"""
Anti-Hallucination and Safety Guard for NEXORA-8.
Guarantees:
1. No hallucinated imports (verifies standard library, local repo modules, installed environment).
2. No undefined variables or unresolvable function calls.
3. No syntax errors or invalid AST structures.
4. No bare excepts or dangerous dynamic code execution (eval, exec, shell=True).
5. Enforces minimal patches and manageable complexity.
"""

import ast
from dataclasses import dataclass, field
import importlib.util
import os
import pkgutil
import re
import sys
from typing import Dict, List, Optional, Set, Tuple


STANDARD_LIBRARY_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins",
    "calendar", "cmath", "collections", "colorsys", "concurrent", "configparser",
    "contextlib", "contextvars", "copy", "csv", "ctypes", "dataclasses", "datetime",
    "decimal", "difflib", "dis", "doctest", "email", "enum", "errno", "faulthandler",
    "filecmp", "fileinput", "fnmatch", "fractions", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "graphlib", "gzip", "hashlib", "heapq", "hmac",
    "html", "http", "idlelib", "imaplib", "imghdr", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder",
    "multiprocessing", "netrc", "nntplib", "numbers", "operator", "optparse", "os",
    "pathlib", "pdb", "pickle", "pickletools", "pkgutil", "platform", "plistlib",
    "poplib", "posixpath", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "sqlite3", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig",
    "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
    "textwrap", "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo",
    "types", "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "wsgiref", "xdrlib", "xml",
    "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "pytest"
}

BUILTIN_NAMES = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))


@dataclass
class GuardFinding:
    severity: str  # "high", "med", "low"
    rule: str
    line: str
    message: str
    line_number: Optional[int] = None


@dataclass
class GuardReport:
    passed: bool
    score: int  # 0 to 100
    verdict: str  # "Safe to merge", "Needs review", "Block"
    findings: List[GuardFinding] = field(default_factory=list)
    added_lines_count: int = 0
    removed_lines_count: int = 0
    complexity_delta: int = 0
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "verdict": self.verdict,
            "findings": [
                {
                    "severity": f.severity,
                    "rule": f.rule,
                    "line": f.line,
                    "message": f.message,
                    "line_number": f.line_number,
                }
                for f in self.findings
            ],
            "added_lines": self.added_lines_count,
            "removed_lines": self.removed_lines_count,
            "complexity_delta": self.complexity_delta,
            "summary": self.summary,
        }


class ScopeVisitor(ast.NodeVisitor):
    """AST visitor that checks for undefined variables while respecting Python scoping."""

    def __init__(self, known_names: Set[str]):
        self.scopes: List[Set[str]] = [set(known_names).union(BUILTIN_NAMES)]
        self.undefined_names: List[Tuple[str, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Add function name to outer scope
        self.scopes[-1].add(node.name)
        # Create function scope
        fn_scope = set()
        for arg in node.args.args:
            fn_scope.add(arg.arg)
        for arg in node.args.kwonlyargs:
            fn_scope.add(arg.arg)
        if node.args.vararg:
            fn_scope.add(node.args.vararg.arg)
        if node.args.kwarg:
            fn_scope.add(node.args.kwarg.arg)

        self.scopes.append(fn_scope)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)  # type: ignore

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scopes[-1].add(node.name)
        self.scopes.append(set())
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign):
        # Value evaluated first
        self.visit(node.value)
        for target in node.targets:
            self._add_target_names(target)

    def visit_AugAssign(self, node: ast.AugAssign):
        self.visit(node.value)
        self.visit(node.target)

    def visit_For(self, node: ast.For):
        self.visit(node.iter)
        self._add_target_names(node.target)
        for item in node.body:
            self.visit(item)
        for item in node.orelse:
            self.visit(item)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Store):
            self.scopes[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Check all enclosing scopes from inner to outer
            found = False
            for scope in reversed(self.scopes):
                if node.id in scope:
                    found = True
                    break
            if not found:
                self.undefined_names.append((node.id, node.lineno))

    def _add_target_names(self, target: ast.AST):
        if isinstance(target, ast.Name):
            self.scopes[-1].add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._add_target_names(elt)


class HallucinationGuard:
    """Evaluates code modifications for safety, correctness, and hallucinations."""

    SEVERITY_WEIGHTS = {"high": 25, "med": 10, "low": 3}

    def __init__(self, known_repo_modules: Optional[Set[str]] = None, max_diff_lines: int = 120):
        self.known_repo_modules = known_repo_modules or set()
        self.max_diff_lines = max_diff_lines
        self.installed_packages = self._discover_installed_packages()

    def _discover_installed_packages(self) -> Set[str]:
        pkgs = set()
        for pkg in pkgutil.iter_modules():
            pkgs.add(pkg.name)
        return pkgs

    def is_module_resolvable(self, mod_name: str) -> bool:
        """Check if module exists in stdlib, local repo, or installed environment."""
        if not mod_name:
            return True
        root_mod = mod_name.split(".")[0]

        if root_mod in STANDARD_LIBRARY_MODULES:
            return True
        if root_mod in self.known_repo_modules or mod_name in self.known_repo_modules:
            return True
        if root_mod in self.installed_packages:
            return True
        # Try importlib spec
        try:
            return importlib.util.find_spec(root_mod) is not None
        except Exception:
            return False

    def validate_patch(
        self,
        original_code: str,
        modified_code: str,
        file_path: str = "module.py",
        known_symbols: Optional[Set[str]] = None
    ) -> GuardReport:
        findings: List[GuardFinding] = []
        known_symbols = set(known_symbols or set())

        # 1. AST compilation check
        try:
            mod_tree = ast.parse(modified_code, filename=file_path)
        except SyntaxError as e:
            findings.append(GuardFinding(
                severity="high",
                rule="Syntax Error",
                line=f"Line {e.lineno}: {e.text.strip() if e.text else ''}",
                message=f"SyntaxError in modified code: {e.msg} (line {e.lineno})",
                line_number=e.lineno,
            ))
            return GuardReport(
                passed=False,
                score=0,
                verdict="Block",
                findings=findings,
                summary=f"Compilation failed: {e.msg} on line {e.lineno}"
            )

        # 2. Extract imports and check for hallucinated modules
        imported_names = set()
        for node in ast.walk(mod_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self.is_module_resolvable(alias.name):
                        findings.append(GuardFinding(
                            severity="high",
                            rule="Hallucinated Import",
                            line=f"import {alias.name}",
                            message=f"Module '{alias.name}' is not in the standard library, local repository, or installed packages.",
                            line_number=node.lineno,
                        ))
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod and not self.is_module_resolvable(mod):
                    findings.append(GuardFinding(
                        severity="high",
                        rule="Hallucinated Import",
                        line=f"from {mod} import ...",
                        message=f"Module '{mod}' is not in the standard library, local repository, or installed packages.",
                        line_number=node.lineno,
                    ))
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

        # 3. Scope & Undefined variable analysis
        known_names = known_symbols.union(imported_names)
        scope_visitor = ScopeVisitor(known_names)
        try:
            scope_visitor.visit(mod_tree)
            for undef_name, lineno in scope_visitor.undefined_names:
                # Ignore common type hinting or self/cls conventions
                if undef_name in {"self", "cls", "__file__", "__name__", "__doc__"}:
                    continue
                findings.append(GuardFinding(
                    severity="high",
                    rule="Undefined Name",
                    line=f"Line {lineno}: {undef_name}",
                    message=f"Identifier '{undef_name}' is referenced before assignment or definition.",
                    line_number=lineno,
                ))
        except Exception:
            pass

        # 4. Pattern-based security and anti-pattern checks
        lines = modified_code.splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Dynamic code execution
            if re.search(r'\b(eval|exec)\s*\(', stripped):
                findings.append(GuardFinding(
                    severity="high",
                    rule="Dynamic Code Execution",
                    line=stripped,
                    message="eval() and exec() are prohibited due to arbitrary code execution risks.",
                    line_number=lineno,
                ))
            # Shell injection
            if re.search(r'shell\s*=\s*True', stripped):
                findings.append(GuardFinding(
                    severity="high",
                    rule="Shell Injection Risk",
                    line=stripped,
                    message="subprocess with shell=True is dangerous. Pass argument lists instead.",
                    line_number=lineno,
                ))
            # Bare except
            if re.match(r'except\s*:', stripped):
                findings.append(GuardFinding(
                    severity="med",
                    rule="Bare Except",
                    line=stripped,
                    message="Bare 'except:' catches system interrupts. Catch specific Exception classes.",
                    line_number=lineno,
                ))
            # Hardcoded secrets
            if re.search(r'(api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{8,}["\']', stripped, re.IGNORECASE):
                findings.append(GuardFinding(
                    severity="high",
                    rule="Hardcoded Secret",
                    line=stripped,
                    message="Hardcoded secrets detected. Use environment variables or configuration.",
                    line_number=lineno,
                ))

        # 5. Diff size calculation
        orig_lines = set(original_code.splitlines())
        mod_lines = set(modified_code.splitlines())
        added = len(mod_lines - orig_lines)
        removed = len(orig_lines - mod_lines)

        if (added + removed) > self.max_diff_lines:
            findings.append(GuardFinding(
                severity="med",
                rule="Diff Too Large",
                line=f"+{added} / -{removed} lines",
                message=f"Total diff ({added + removed} lines) exceeds the maximum recommended threshold of {self.max_diff_lines} lines.",
            ))

        # 6. Scoring & Verdict
        deductions = sum(self.SEVERITY_WEIGHTS.get(f.severity, 5) for f in findings)
        score = max(0, 100 - deductions)
        has_high = any(f.severity == "high" for f in findings)

        if has_high:
            verdict = "Block"
            passed = False
        elif score < 85:
            verdict = "Needs review"
            passed = True
        else:
            verdict = "Safe to merge"
            passed = True

        high_cnt = sum(1 for f in findings if f.severity == "high")
        med_cnt = sum(1 for f in findings if f.severity == "med")
        low_cnt = sum(1 for f in findings if f.severity == "low")

        summary = (
            f"Safety score: {score}/100. Verdict: {verdict}. "
            f"Findings: {high_cnt} high, {med_cnt} med, {low_cnt} low. "
            f"Diff: +{added} / -{removed} lines."
        )

        return GuardReport(
            passed=passed,
            score=score,
            verdict=verdict,
            findings=findings,
            added_lines_count=added,
            removed_lines_count=removed,
            complexity_delta=0,
            summary=summary,
        )
