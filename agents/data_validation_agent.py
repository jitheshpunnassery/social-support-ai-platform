"""
Data Validation Agent
----------------------
Cross-checks extracted fields across documents and against the applicant's
self-reported form data to surface inconsistencies automatically: address
mismatches (form vs credit bureau), income variance across documents,
name/date-of-birth/nationality mismatches (form vs Emirates ID), expired
IDs, etc.

Uses a ReAct loop: for each consistency rule, THOUGHT -> ACTION (comparison)
-> OBSERVATION (flag or pass). The plain-language summary in this phase is
template-based; Phase 8 upgrades it to use the local LLM for a more natural
case-officer-facing summary, falling back to this template when the LLM is
unreachable.
"""
import difflib

from agents.base import BaseAgent
from agents.llm_client import llm_client


class DataValidationAgent(BaseAgent):
    name = "data_validation_agent"

    def run(self, state: dict) -> dict:
        self.think(state, "Cross-checking extracted document fields against the application "
                           "form and against each other for inconsistencies.")
        form = state.get("form_data", {})
        extracted = state.get("extracted_data", {})
        flags = []

        flags += self.act(state, "check name consistency", lambda: self._check_name(form, extracted))
        flags += self.act(state, "check date of birth consistency", lambda: self._check_date_of_birth(form, extracted))
        flags += self.act(state, "check nationality consistency", lambda: self._check_nationality(form, extracted))
        flags += self.act(state, "check address consistency", lambda: self._check_address(form, extracted))
        flags += self.act(state, "check income consistency", lambda: self._check_income(form, extracted))
        flags += self.act(state, "check ID validity", lambda: self._check_id_validity(extracted))

        severity = "none"
        if any(f["severity"] == "high" for f in flags):
            severity = "high"
        elif flags:
            severity = "medium"

        report = {"flags": flags, "overall_severity": severity, "requires_human_review": severity == "high"}

        if flags:
            llm_summary = llm_client.chat(
                "You are a compliance assistant. Summarize data-consistency findings for a case "
                "officer in 2-3 plain sentences, non-accusatory tone.",
                f"Findings: {flags}",
            )
            report["summary"] = llm_summary or self._template_summary(flags)
        else:
            report["summary"] = self._template_summary(flags)

        state["validation_report"] = report
        self.think(state, f"Validation complete. Overall severity: {severity}. "
                           f"{len(flags)} flag(s) raised.")
        return state

    @staticmethod
    def _template_summary(flags: list) -> str:
        if not flags:
            return "No material inconsistencies found across submitted documents."
        fields = ", ".join(f["field"] for f in flags)
        return f"{len(flags)} consistency flag(s) raised on: {fields}. See details for specifics."

    def _check_name(self, form, extracted) -> list:
        flags = []
        form_name = (form.get("full_name") or "").strip().lower()
        id_name = ((extracted.get("emirates_id") or {}).get("name_en") or "").strip().lower()
        if form_name and id_name:
            ratio = difflib.SequenceMatcher(None, form_name, id_name).ratio()
            if ratio < 0.75:
                flags.append({"field": "full_name", "severity": "high",
                               "detail": f"Form name '{form.get('full_name')}' doesn't match "
                                         f"Emirates ID name on record."})
        return flags

    def _check_date_of_birth(self, form, extracted) -> list:
        flags = []
        form_dob = (form.get("date_of_birth") or "").strip()
        id_dob = ((extracted.get("emirates_id") or {}).get("date_of_birth") or "").strip()
        if form_dob and id_dob and form_dob != id_dob:
            flags.append({"field": "date_of_birth", "severity": "high",
                           "detail": f"Form date of birth ({form_dob}) doesn't match the date of "
                                     f"birth on the Emirates ID record ({id_dob})."})
        return flags

    def _check_nationality(self, form, extracted) -> list:
        flags = []
        form_nat = (form.get("nationality") or "").strip().lower()
        id_nat = ((extracted.get("emirates_id") or {}).get("nationality") or "").strip().lower()
        if form_nat and id_nat and form_nat != id_nat:
            flags.append({"field": "nationality", "severity": "medium",
                           "detail": f"Form nationality ('{form.get('nationality')}') differs from the "
                                     f"nationality on the Emirates ID record ('{(extracted.get('emirates_id') or {}).get('nationality')}')."})
        return flags

    def _check_address(self, form, extracted) -> list:
        flags = []
        form_address = (form.get("address") or "").strip().lower()
        credit_address = ((extracted.get("credit_report") or {}).get("address_on_file") or "").strip().lower()
        if form_address and credit_address:
            ratio = difflib.SequenceMatcher(None, form_address, credit_address).ratio()
            if ratio < 0.5:
                flags.append({"field": "address", "severity": "medium",
                               "detail": "Address on application form differs from credit bureau "
                                         "record; may indicate a recent move not yet updated."})
        return flags

    def _check_income(self, form, extracted) -> list:
        flags = []
        form_income = form.get("monthly_income")
        bank = extracted.get("bank_statement") or {}
        bank_flow = bank.get("avg_monthly_net_flow")
        if form_income is not None and bank_flow is not None:
            try:
                if abs(float(form_income) - float(bank_flow)) > max(1000, 0.4 * float(form_income or 1)):
                    flags.append({"field": "monthly_income", "severity": "medium",
                                   "detail": f"Self-reported income (AED {form_income}) diverges "
                                             f"materially from bank statement net flow (AED {bank_flow})."})
            except (TypeError, ValueError):
                pass
        return flags

    def _check_id_validity(self, extracted) -> list:
        flags = []
        eid = extracted.get("emirates_id") or {}
        expiry = eid.get("expiry_date")
        if expiry:
            from datetime import date
            try:
                if date.fromisoformat(expiry) < date.today():
                    flags.append({"field": "emirates_id.expiry_date", "severity": "high",
                                   "detail": f"Emirates ID expired on {expiry}."})
            except ValueError:
                pass
        return flags
