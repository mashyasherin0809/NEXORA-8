"""Schema-constrained prompt templates used by the RepoPilot agents."""

from __future__ import annotations

import json
from typing import Any, Dict


SCHEMAS: Dict[str, Dict[str, Any]] = {
    "task_plan": {
        "type": "object", "additionalProperties": False,
        "required": ["goal", "task_type", "search_keywords", "candidate_symbols", "validation_strategy"],
        "properties": {
            "goal": {"type": "string"},
            "task_type": {"type": "string", "enum": ["bug", "feature", "refactor"]},
            "search_keywords": {"type": "array", "items": {"type": "string"}},
            "candidate_symbols": {"type": "array", "items": {"type": "string"}},
            "validation_strategy": {"type": "string"},
        },
    },
    "root_cause": {
        "type": "object", "additionalProperties": False,
        "required": ["root_cause", "why", "confidence", "target_files", "target_symbols"],
        "properties": {
            "root_cause": {"type": "string"}, "why": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "target_files": {"type": "array", "items": {"type": "string"}},
            "target_symbols": {"type": "array", "items": {"type": "string"}},
        },
    },
    "patch": {
        "type": "object", "additionalProperties": False,
        "required": ["patches"],
        "properties": {"patches": {"type": "array", "maxItems": 5, "items": {
            "type": "object", "additionalProperties": False,
            "required": ["file", "search", "replace", "explanation"],
            "properties": {"file": {"type": "string"}, "search": {"type": "string"},
                           "replace": {"type": "string"}, "explanation": {"type": "string"}},
        }}},
    },
    "review": {
        "type": "object", "additionalProperties": False,
        "required": ["approved", "risk", "findings", "plain_english"],
        "properties": {"approved": {"type": "boolean"}, "risk": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                       "findings": {"type": "array", "items": {"type": "string"}}, "plain_english": {"type": "string"}},
    },
    "verdict": {
        "type": "object", "additionalProperties": False,
        "required": ["verdict", "confidence", "reason", "regressions", "coverage"],
        "properties": {"verdict": {"type": "string", "enum": ["VERIFIED", "ROLLED_BACK", "NEEDS_REVIEW"]},
                       "confidence": {"type": "number", "minimum": 0, "maximum": 1}, "reason": {"type": "string"},
                       "regressions": {"type": "array", "items": {"type": "string"}},
                       "coverage": {"type": "string"}},
    },
}


def render(template: str, context: Dict[str, Any]) -> str:
    """Render a prompt with a schema declaration and JSON-only output contract."""
    schema = json.dumps(SCHEMAS[template], indent=2)
    values = "\n".join(f"{key.upper()}:\n{value}" for key, value in context.items())
    return f"""You are RepoPilot, an autonomous software engineer.
{values}

Return JSON only. Do not invent files, symbols, dependencies, or test results.
Your response MUST validate against this JSON Schema:
{schema}
"""
