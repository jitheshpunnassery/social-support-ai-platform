"""
Unified tracing helper. In Phase 1, this only appends steps to an in-memory
`state['trace']` list -- this is what will eventually drive the Streamlit
"agent reasoning" panel (Phase 6) and get mirrored to Langfuse (Phase 10)
and persisted to a database table (Phase 7). Those integrations are added
incrementally in their respective phases without changing this function's
signature, so agents written against it never need to change.
"""
import logging

logger = logging.getLogger(__name__)


def trace_step(state: dict, agent_name: str, step_type: str, content: str):
    """Record one ReAct step (thought | action | observation) for an agent."""
    state.setdefault("trace", []).append({
        "agent": agent_name, "type": step_type, "content": content,
    })
    logger.debug("[%s] %s: %s", agent_name, step_type, content)
