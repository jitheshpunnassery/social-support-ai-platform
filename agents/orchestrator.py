"""
Master Orchestrator
---------------------
Coordinates the specialist agents into the end-to-end application workflow:

  intake -> data_extraction -> data_validation -> eligibility_assessment
         -> decision -> enablement_recommendation -> finalize

(Phase 9 adds the `enablement_recommendation` node after `decision`; it
runs for every applicant, not only declines, to surface upskilling/job-
matching support alongside the financial-support decision.)

Orchestration tool: LangGraph (StateGraph) defines this as an explicit,
inspectable graph. If LangGraph isn't installed, a functionally equivalent
sequential executor runs instead, so the pipeline still works end-to-end in
restricted/offline environments.

Reasoning framework: each specialist agent internally follows a ReAct loop
(Thought -> Action -> Observation), recorded via observability/tracing.py.
"""
import logging
import time

from agents.data_extraction_agent import DataExtractionAgent
from agents.data_validation_agent import DataValidationAgent
from agents.eligibility_agent import EligibilityAgent
from agents.decision_agent import DecisionAgent
from agents.enablement_agent import EnablementAgent
from observability.tracing import trace_step

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except Exception:  # noqa: BLE001
    LANGGRAPH_AVAILABLE = False


_extraction = DataExtractionAgent()
_validation = DataValidationAgent()
_eligibility = EligibilityAgent()
_decision = DecisionAgent()
_enablement = EnablementAgent()


def _node_intake(state: dict) -> dict:
    trace_step(state, "master_orchestrator", "thought",
               "New application received. Routing to Data Extraction Agent.")
    return state


def _node_finalize(state: dict) -> dict:
    trace_step(state, "master_orchestrator", "thought",
               f"Pipeline complete. Final decision: {state.get('decision')}.")
    return state


def build_graph():
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(dict)
    graph.add_node("intake", _node_intake)
    graph.add_node("data_extraction", _extraction.run)
    graph.add_node("data_validation", _validation.run)
    graph.add_node("eligibility_assessment", _eligibility.run)
    graph.add_node("decision", _decision.run)
    graph.add_node("enablement_recommendation", _enablement.run)
    graph.add_node("finalize", _node_finalize)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "data_extraction")
    graph.add_edge("data_extraction", "data_validation")
    graph.add_edge("data_validation", "eligibility_assessment")
    graph.add_edge("eligibility_assessment", "decision")
    graph.add_edge("decision", "enablement_recommendation")
    graph.add_edge("enablement_recommendation", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


_compiled_graph = build_graph() if LANGGRAPH_AVAILABLE else None

_SEQUENTIAL_STEPS = [
    ("intake", _node_intake),
    ("data_extraction", _extraction.run),
    ("data_validation", _validation.run),
    ("eligibility_assessment", _eligibility.run),
    ("decision", _decision.run),
    ("enablement_recommendation", _enablement.run),
    ("finalize", _node_finalize),
]


def run_application(state: dict) -> dict:
    """Entry point used by the API layer (added in Phase 6). `state` must
    contain at least `form_data` and `raw_documents`."""
    start = time.perf_counter()

    if LANGGRAPH_AVAILABLE and _compiled_graph is not None:
        logger.info("Running pipeline via LangGraph.")
        state = _compiled_graph.invoke(state)
    else:
        logger.info("LangGraph not installed - running equivalent sequential ReAct pipeline.")
        for step_name, fn in _SEQUENTIAL_STEPS:
            state = fn(state)

    state["processing_seconds"] = round(time.perf_counter() - start, 3)
    return state
