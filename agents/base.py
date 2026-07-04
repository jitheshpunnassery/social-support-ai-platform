"""
Base class for all agents. Implements a ReAct-style loop contract:
each agent records THOUGHT -> ACTION -> OBSERVATION steps into a shared
trace list (mirrored to Langfuse when configured, and to the local
AgentTrace table for auditability without external dependencies).
"""
import logging
import time
from typing import Any, Callable

from observability.tracing import trace_step

logger = logging.getLogger(__name__)


class BaseAgent:
    name: str = "base_agent"

    def __init__(self):
        self.logger = logging.getLogger(self.name)

    def think(self, state: dict, thought: str):
        trace_step(state, self.name, "thought", thought)

    def act(self, state: dict, action: str, fn: Callable[[], Any]):
        trace_step(state, self.name, "action", action)
        start = time.perf_counter()
        result = fn()
        elapsed = round(time.perf_counter() - start, 4)
        trace_step(state, self.name, "observation", f"completed in {elapsed}s")
        return result

    def run(self, state: dict) -> dict:
        raise NotImplementedError
