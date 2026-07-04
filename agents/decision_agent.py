"""
Decision Recommendation Agent
-------------------------------
Combines the eligibility ML score with the data-validation report to make
(or recommend) a final decision, applying the department's threshold
policy. High-severity data inconsistencies always force human review
regardless of the ML score, keeping a human-in-the-loop safety net around
subjective/ambiguous cases.

The explanation text in this phase is templated. Phase 8 upgrades it to
use the local LLM for a warmer, more natural explanation, falling back to
this template when the LLM is unreachable.
"""
from agents.base import BaseAgent
from config import settings


class DecisionAgent(BaseAgent):
    name = "decision_agent"

    def run(self, state: dict) -> dict:
        self.think(state, "Applying department policy thresholds to the eligibility score, "
                           "accounting for any data-validation flags.")
        score = state.get("ml_score", 0.0)
        validation = state.get("validation_report", {})

        decision, reason = self.act(
            state, "apply threshold policy",
            lambda: self._decide(score, validation))

        state["decision"] = decision
        state["decision_reason"] = reason
        self.think(state, f"Final decision: {decision}")
        return state

    def _decide(self, score: float, validation: dict):
        if validation.get("requires_human_review"):
            return "needs_human_review", ("Routed to a human case officer due to unresolved "
                                            "document-consistency flags that require manual verification.")
        if score >= settings.AUTO_APPROVE_THRESHOLD:
            return "approved", f"Approved automatically (eligibility score {score:.2f})."
        if score <= settings.AUTO_DECLINE_THRESHOLD:
            return "soft_declined", (f"Soft-declined for direct financial support (eligibility score "
                                       f"{score:.2f}); economic enablement support is recommended instead.")
        return "needs_human_review", (f"Borderline eligibility score ({score:.2f}) routed to a human "
                                        f"case officer for final judgment.")
