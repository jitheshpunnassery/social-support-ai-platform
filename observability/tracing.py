"""
Unified tracing helper. Every agent step is:
  1. appended to state['trace'] (in-memory, always available, drives the
     Streamlit "agent reasoning" panel in real time), and
  2. forwarded to Langfuse when LANGFUSE_PUBLIC_KEY/SECRET_KEY are set
     (end-to-end observability: latency, cost, prompt/response pairs,
     per-agent spans), and
  3. persisted to the local AgentTrace table for durable audit history
     (case officers can review *why* a decision was made after the fact).
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
    state.setdefault("trace", []).append({
        "agent": agent_name, "type": step_type, "content": content,
    })

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
