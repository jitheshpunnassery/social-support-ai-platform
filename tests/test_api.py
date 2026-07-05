"""Phase 10: end-to-end API tests covering submission, persistence,
enablement recommendations, and the RAG chatbot -- the full system as it
stands after all 10 phases."""
import json
import os

import pytest
from fastapi.testclient import TestClient

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE, "data", "synthetic", "sample_documents")


@pytest.fixture(scope="module")
def client():
    from data.synthetic_data_generator import generate_sample_documents
    if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
        generate_sample_documents(5)

    from api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def submitted_application(client):
    with open(os.path.join(DOC_DIR, "bank_statement_1.txt"), "rb") as bs, \
         open(os.path.join(DOC_DIR, "emirates_id_1.json"), "rb") as eid, \
         open(os.path.join(DOC_DIR, "resume_1.txt"), "rb") as res, \
         open(os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"), "rb") as al, \
         open(os.path.join(DOC_DIR, "credit_report_1.txt"), "rb") as cr:

        resp = client.post(
            "/applications",
            data={"full_name": "Test Applicant", "emirates_id": "784-1990-1234567-1",
                  "date_of_birth": "1990-05-15", "gender": "Male", "nationality": "UAE",
                  "marital_status": "Single", "mobile_number": "+971501234567",
                  "email": "test.applicant@example.com", "emirate": "Dubai",
                  "residency_status": "UAE National",
                  "family_size": 5, "employment_status": "unemployed", "monthly_income": 900,
                  "address": "123 Sheikh Zayed Road, Dubai"},
            files={
                "bank_statement": ("bank_statement_1.txt", bs, "text/plain"),
                "emirates_id_doc": ("emirates_id_1.json", eid, "application/json"),
                "resume": ("resume_1.txt", res, "text/plain"),
                "assets_liabilities": ("assets_liabilities_1.xlsx", al,
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "credit_report": ("credit_report_1.txt", cr, "text/plain"),
            },
        )
    assert resp.status_code == 200
    return resp.json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_submit_application_returns_decision(submitted_application):
    assert submitted_application["decision"] in {"approved", "soft_declined", "needs_human_review"}
    assert 0.0 <= submitted_application["ml_score"] <= 1.0
    assert len(submitted_application["trace"]) > 0


def test_application_status_persisted(client, submitted_application):
    app_id = submitted_application["application_id"]
    resp = client.get(f"/applications/{app_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == submitted_application["status"]


def test_enablement_recommendations_present(submitted_application):
    assert submitted_application["enablement_recommendations"] is not None
    assert len(submitted_application["enablement_recommendations"]) > 0


def test_chat_endpoint_grounded_reply(client, submitted_application):
    resp = client.post("/chat", json={"application_id": submitted_application["application_id"],
                                        "message": "What documents do I need to provide?"})
    assert resp.status_code == 200
    assert len(resp.json()["reply"]) > 0


def test_missing_application_returns_404(client):
    resp = client.get("/applications/does-not-exist")
    assert resp.status_code == 404
