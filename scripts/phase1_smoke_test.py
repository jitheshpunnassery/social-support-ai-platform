"""Phase 1 smoke test: confirms the project scaffolding, config, and base
agent/tracing infrastructure import and behave correctly, with no
dependency on any agent implemented in later phases."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from agents.base import BaseAgent


class PingAgent(BaseAgent):
    name = "ping_agent"

    def run(self, state: dict) -> dict:
        self.think(state, "Just checking that the trace mechanism works.")
        result = self.act(state, "ping", lambda: "pong")
        state["ping_result"] = result
        return state


if __name__ == "__main__":
    print("AUTO_APPROVE_THRESHOLD:", settings.AUTO_APPROVE_THRESHOLD)
    state = {}
    state = PingAgent().run(state)
    assert state["ping_result"] == "pong"
    assert len(state["trace"]) == 3  # thought, action, observation
    print("Trace:", state["trace"])
    print("Phase 1 scaffolding OK.")
