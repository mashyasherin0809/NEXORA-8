"""
Base Agent class and telemetry events for NEXORA-8 Multi-Agent System.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentEvent:
    timestamp: float
    agent_name: str
    stage: str
    event_type: str  # "status_change", "log", "metric", "gate_check", "diff_generated"
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": round(self.timestamp, 3),
            "agent_name": self.agent_name,
            "stage": self.stage,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data or {},
        }


class BaseAgent:
    """Base class for all specialized sub-agents in NEXORA-8."""

    def __init__(self, name: str, role_description: str):
        self.name = name
        self.role_description = role_description
        self.status = AgentStatus.IDLE
        self.logs: List[str] = []
        self.event_callbacks: List[Callable[[AgentEvent], None]] = []

    def add_event_listener(self, callback: Callable[[AgentEvent], None]):
        self.event_callbacks.append(callback)

    def set_status(self, status: AgentStatus, message: str = "", data: Optional[Dict] = None):
        self.status = status
        event = AgentEvent(
            timestamp=time.time(),
            agent_name=self.name,
            stage=self.name,
            event_type="status_change",
            message=message or f"{self.name} is now {status.value}",
            data=data,
        )
        self._emit(event)

    def log(self, message: str, data: Optional[Dict] = None):
        self.logs.append(message)
        event = AgentEvent(
            timestamp=time.time(),
            agent_name=self.name,
            stage=self.name,
            event_type="log",
            message=message,
            data=data,
        )
        self._emit(event)

    def _emit(self, event: AgentEvent):
        for cb in self.event_callbacks:
            try:
                cb(event)
            except Exception:
                pass
