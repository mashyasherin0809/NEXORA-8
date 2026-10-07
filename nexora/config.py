"""
Global configuration module for NEXORA-8 Agent.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    """NEXORA-8 System Configuration."""

    # Model configuration
    model_provider: str = os.getenv("LLM_PROVIDER", os.getenv("NEXORA_MODEL_PROVIDER", "gemini"))
    model_name: str = os.getenv("LLM_MODEL", os.getenv("NEXORA_MODEL_NAME", "gemini-2.5-flash"))
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY", os.getenv("LLM_API_KEY"))
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY"))
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY", os.getenv("LLM_API_KEY"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Execution & verification settings
    max_repair_attempts: int = int(os.getenv("NEXORA_MAX_ATTEMPTS", "3"))
    test_timeout_seconds: int = int(os.getenv("NEXORA_TEST_TIMEOUT", "45"))
    max_diff_lines: int = int(os.getenv("NEXORA_MAX_DIFF_LINES", "120"))
    max_changed_files: int = int(os.getenv("NEXORA_MAX_CHANGED_FILES", "5"))
    max_added_lines: int = int(os.getenv("NEXORA_MAX_ADDED_LINES", "80"))
    max_test_timeout_seconds: int = int(os.getenv("NEXORA_TEST_TIMEOUT", "300"))
    sandbox_base_dir: Optional[str] = os.getenv("NEXORA_SANDBOX_DIR", None)

    # Server settings
    server_host: str = os.getenv("NEXORA_SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("NEXORA_SERVER_PORT", "5000"))

    # Safety Guard Configuration
    strict_import_check: bool = True
    block_bare_except: bool = True
    block_eval_exec: bool = True
    block_unresolved_calls: bool = True

    # Telemetry
    track_tokens: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
