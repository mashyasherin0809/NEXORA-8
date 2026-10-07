"""Language-specific repository analysis and test execution contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


@dataclass
class TestRun:
    command: List[str]
    passed: bool
    return_code: int
    output: str
    duration: float
    tests: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"command": self.command, "passed": self.passed, "return_code": self.return_code,
                "output": self.output[-12000:], "duration": round(self.duration, 2), "tests": self.tests}


class LanguageAdapter(ABC):
    language: str
    build_system: str
    test_command: List[str]

    @abstractmethod
    def detect(self, root: str) -> bool:
        """Return whether this adapter owns the repository."""

    @abstractmethod
    def analyze(self, root: str) -> Dict[str, Any]:
        """Return a serializable structural summary."""

    def run_tests(self, root: str, timeout: int = 120) -> TestRun:
        started = time.time()
        try:
            result = subprocess.run(self.test_command, cwd=root, text=True, capture_output=True, timeout=timeout)
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            return TestRun(self.test_command, result.returncode == 0, result.returncode, output, time.time() - started)
        except subprocess.TimeoutExpired as exc:
            output = f"Test command timed out after {timeout}s\n{exc.stdout or ''}\n{exc.stderr or ''}"
            return TestRun(self.test_command, False, -1, output, time.time() - started)
        except OSError as exc:
            return TestRun(self.test_command, False, -1, str(exc), time.time() - started)

    def compile(self, root: str, timeout: int = 120) -> TestRun:
        """Compile using the adapter's safe, fixed command when supported."""
        return TestRun([], True, 0, "Compilation is not defined for this adapter.", 0.0)


class MavenJavaAdapter(LanguageAdapter):
    language = "java"
    build_system = "maven"
    test_command = ["mvn", "-q", "test"]
    compile_command = ["mvn", "-q", "compile"]

    def detect(self, root: str) -> bool:
        return os.path.isfile(os.path.join(root, "pom.xml"))

    def analyze(self, root: str) -> Dict[str, Any]:
        java_files = []
        test_files = []
        classes = 0
        methods = 0
        for path in Path(root).rglob("*.java"):
            if any(part in {"target", ".git", ".mvn"} for part in path.parts):
                continue
            relative = path.relative_to(root).as_posix()
            content = path.read_text(encoding="utf-8", errors="replace")
            classes += content.count(" class ") + content.count(" interface ")
            methods += content.count("(")
            item = {"path": relative, "lines": len(content.splitlines()), "classes": content.count(" class ")}
            (test_files if "/test/" in f"/{relative}" else java_files).append(item)
        return {"language": self.language, "build_system": self.build_system, "test_framework": "JUnit",
                "source_directories": ["src/main/java"], "test_directories": ["src/test/java"],
                "files": len(java_files) + len(test_files), "classes": classes, "methods": methods,
                "tests": len(test_files), "source_files": java_files, "test_files": test_files}

    def compile(self, root: str, timeout: int = 120) -> TestRun:
        return self._run_maven(root, self.compile_command, timeout)

    def run_tests(self, root: str, timeout: int = 120) -> TestRun:
        result = self._run_maven(root, self.test_command, timeout)
        report_dir = Path(root) / "target" / "surefire-reports"
        for report in report_dir.glob("TEST-*.xml"):
            try:
                suite = ET.parse(report).getroot()
                for case in suite.findall("testcase"):
                    status = "passed"
                    failure = case.find("failure")
                    error = case.find("error")
                    skipped = case.find("skipped")
                    if failure is not None:
                        status = "failed"
                    elif error is not None:
                        status = "error"
                    elif skipped is not None:
                        status = "skipped"
                    result.tests.append({"id": f"{suite.attrib.get('name', report.stem)}::{case.attrib.get('name', 'unknown')}",
                                         "status": status, "duration": float(case.attrib.get("time", "0"))})
            except (ET.ParseError, ValueError):
                continue
        return result

    def _run_maven(self, root: str, command: List[str], timeout: int) -> TestRun:
        started = time.time()
        try:
            result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            return TestRun(command, result.returncode == 0, result.returncode, output, time.time() - started)
        except subprocess.TimeoutExpired as exc:
            return TestRun(command, False, -1, f"Maven timed out after {timeout}s\n{exc.stdout or ''}", time.time() - started)
        except OSError as exc:
            return TestRun(command, False, -1, str(exc), time.time() - started)


class PythonAdapter(LanguageAdapter):
    language = "python"
    build_system = "pytest"
    test_command = ["python", "-m", "pytest", "-q"]

    def detect(self, root: str) -> bool:
        return os.path.isfile(os.path.join(root, "requirements.txt")) or any(Path(root).rglob("*.py"))

    def analyze(self, root: str) -> Dict[str, Any]:
        from nexora.analyzer.repo_indexer import CodebaseIndexer
        index = CodebaseIndexer(root).index()
        return {"language": self.language, "build_system": self.build_system, "test_framework": "pytest",
                "files": index.total_files, "classes": sum(len(f.classes) for f in index.files.values()),
                "methods": index.total_symbols, "tests": index.total_tests}


class NodeAdapter(LanguageAdapter):
    language = "javascript"
    build_system = "npm"
    test_command = ["npm", "test", "--", "--runInBand"]

    def detect(self, root: str) -> bool:
        return os.path.isfile(os.path.join(root, "package.json"))

    def analyze(self, root: str) -> Dict[str, Any]:
        return {"language": self.language, "build_system": self.build_system, "test_framework": "jest (stub)",
                "files": sum(1 for _ in Path(root).rglob("*.js"))}


ADAPTERS = (MavenJavaAdapter(), PythonAdapter(), NodeAdapter())


def adapter_for(root: str) -> LanguageAdapter:
    for adapter in ADAPTERS:
        if adapter.detect(root):
            return adapter
    raise ValueError("Unsupported repository: expected pom.xml, package.json, or a Python project")