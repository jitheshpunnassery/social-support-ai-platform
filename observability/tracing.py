"""
Unified tracing helper.

Phase 1:  appended steps to an in-memory `state['trace']` list only.
Phase 7:  also persists each step to the `agent_traces` table once a
          database session + application_id are present in `state`.
Phase 10: also mirrors each step to Langfuse when LANGFUSE_PUBLIC_KEY /
          LANGFUSE_SECRET_KEY are configured, giving end-to-end latency,
          cost, and prompt/response observability across the whole
          pipeline. All three sinks are independent and best-effort --
          agents never need to change because they only ever call
          `trace_step(...)`.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)

_langfuse_client = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Langfuse unavailable (%s); continuing without it.", e)


def trace_step(state: dict, agent_name: str, step_type: str, content: str):
    """Record one ReAct step (thought | action | observation) for an agent."""
    state.setdefault("trace", []).append({
        "agent": agent_name, "type": step_type, "content": content,
    })
    logger.debug("[%s] %s: %s", agent_name, step_type, content)

    if _langfuse_client is not None:
        try:
            trace = _langfuse_client.trace(
                name=f"application-{state.get('application_id', 'unknown')}",
                id=state.get("application_id"),
            )
            trace.span(name=f"{agent_name}:{step_type}", input=content)
        except Exception as e:  # noqa: BLE001
            logger.debug("Langfuse trace write failed: %s", e)

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
