"""
Tests for NEXORA-8 Anti-Hallucination and Deterministic Safety Guard.
"""

import pytest
from nexora.guard.hallucination_guard import HallucinationGuard


def test_guard_blocks_hallucinated_imports():
    guard = HallucinationGuard(known_repo_modules={"my_app", "utils"})
    
    # Fake/made-up package
    bad_code = "import super_fake_ai_lib_that_does_not_exist\n\ndef run():\n    return 42\n"
    report = guard.validate_patch(original_code="", modified_code=bad_code)

    assert not report.passed
    assert report.verdict == "Block"
    assert any(f.rule == "Hallucinated Import" for f in report.findings)


def test_guard_allows_standard_library_and_known_modules():
    guard = HallucinationGuard(known_repo_modules={"my_app"})
    
    valid_code = "import os\nimport math\nfrom decimal import Decimal\n\ndef compute():\n    return math.pi\n"
    report = guard.validate_patch(original_code="", modified_code=valid_code)

    assert report.passed
    assert report.score >= 85
    assert not any(f.rule == "Hallucinated Import" for f in report.findings)


def test_guard_blocks_undefined_names():
    guard = HallucinationGuard()
    
    undef_code = "def process():\n    return undefined_variable_xyz * 2\n"
    report = guard.validate_patch(original_code="", modified_code=undef_code)

    assert not report.passed
    assert any(f.rule == "Undefined Name" for f in report.findings)


def test_guard_flags_security_anti_patterns():
    guard = HallucinationGuard()

    eval_code = "def run(x):\n    eval(x)\n"
    report = guard.validate_patch(original_code="", modified_code=eval_code)
    assert any(f.rule == "Dynamic Code Execution" for f in report.findings)

    bare_except_code = "def run():\n    try:\n        pass\n    except:\n        pass\n"
    report = guard.validate_patch(original_code="", modified_code=bare_except_code)
    assert any(f.rule == "Bare Except" for f in report.findings)
