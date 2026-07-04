import json
import os

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE, "data", "synthetic", "sample_documents")


@pytest.fixture(scope="module")
def sample_state():
    with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
        emirates_id = json.load(f)
    with open(os.path.join(DOC_DIR, "bank_statement_1.txt")) as f:
        bank_statement = f.read()
    with open(os.path.join(DOC_DIR, "resume_1.txt")) as f:
        resume = f.read()
    with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
        credit_report = f.read()

    return {
        "application_id": "TEST-PYTEST",
        "form_data": {
            "full_name": emirates_id["name_en"],
            "address": "123 Sheikh Zayed Road, Dubai",
            "family_size": 4,
            "employment_status": "unemployed",
            "monthly_income": 1200,
            "months_employed": 0,
        },
        "raw_documents": {
            "bank_statement": bank_statement,
            "emirates_id": emirates_id,
            "resume": resume,
            "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"),
            "credit_report": credit_report,
        },
    }


def test_extraction_agent(sample_state):
    from agents.data_extraction_agent import DataExtractionAgent
    state = dict(sample_state)
    result = DataExtractionAgent().run(state)
    assert "extracted_data" in result
    assert "assets_liabilities" in result["extracted_data"]
    assert result["extracted_data"]["assets_liabilities"]["total_assets"] >= 0


def test_eligibility_agent_scores_between_0_and_1(sample_state):
    from agents.data_extraction_agent import DataExtractionAgent
    from agents.eligibility_agent import EligibilityAgent
    state = DataExtractionAgent().run(dict(sample_state))
    state = EligibilityAgent().run(state)
    assert 0.0 <= state["ml_score"] <= 1.0


def test_full_pipeline_produces_decision(sample_state):
    from agents.orchestrator import run_application
    result = run_application(dict(sample_state))
    assert result["decision"] in {"approved", "soft_declined", "needs_human_review"}
    assert "trace" in result and len(result["trace"]) > 0


def test_validation_flags_expired_id(sample_state):
    from agents.data_extraction_agent import DataExtractionAgent
    from agents.data_validation_agent import DataValidationAgent
    state = dict(sample_state)
    state["raw_documents"] = dict(state["raw_documents"])
    expired_id = dict(json.loads(open(os.path.join(DOC_DIR, "emirates_id_1.json")).read()))
    expired_id["expiry_date"] = "2020-01-01"
    state["raw_documents"]["emirates_id"] = expired_id

    state = DataExtractionAgent().run(state)
    state = DataValidationAgent().run(state)
    fields_flagged = [f["field"] for f in state["validation_report"]["flags"]]
    assert "emirates_id.expiry_date" in fields_flagged
    assert state["validation_report"]["requires_human_review"] is True
