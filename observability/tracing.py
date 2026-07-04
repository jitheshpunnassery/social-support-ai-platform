"""
Unified tracing helper.

Phase 1: appended steps to an in-memory `state['trace']` list only.
Phase 7 change: when a database session and application_id are present in
`state` (set by the API layer once PostgreSQL is connected), each step is
also persisted to the `agent_traces` table for durable audit history --
case officers can review *why* a decision was made after the fact, even if
the in-memory trace was never viewed. Langfuse mirroring is added in
Phase 10 as a third, independent sink; agents never need to change because
they only ever call `trace_step(...)`.
"""
import logging

logger = logging.getLogger(__name__)


def trace_step(state: dict, agent_name: str, step_type: str, content: str):
    """Record one ReAct step (thought | action | observation) for an agent."""
    state.setdefault("trace", []).append({
        "agent": agent_name, "type": step_type, "content": content,
    })
    logger.debug("[%s] %s: %s", agent_name, step_type, content)

    db_session = state.get("db_session")
    application_id = state.get("application_id")
    if db_session is not None and application_id:
        try:
            from db.models import AgentTrace
            db_session.add(AgentTrace(application_id=application_id, agent_name=agent_name,
                                       step=step_type, content=content))
            db_session.commit()
        except Exception as e:  # noqa: BLE001
            logger.debug("Local trace persist failed: %s", e)
