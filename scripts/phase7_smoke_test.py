"""Phase 7 smoke test: same flow as Phase 6, but now confirms records
survive in the database (SQLite fallback if PostgreSQL isn't running) by
re-fetching the application in a fresh request, plus checks the local
agent_traces audit table was populated."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure a clean local DB for a repeatable test run
LOCAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.db")
if os.path.exists(LOCAL_DB):
    os.remove(LOCAL_DB)

from fastapi.testclient import TestClient
from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from api.main import app
from db.database import SessionLocal
from db.models import AgentTrace, Applicant

if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

with TestClient(app) as client:
    print("Health:", client.get("/health").json())

    with open(os.path.join(DOC_DIR, "bank_statement_1.txt"), "rb") as bs, \
         open(os.path.join(DOC_DIR, "emirates_id_1.json"), "rb") as eid, \
         open(os.path.join(DOC_DIR, "resume_1.txt"), "rb") as res, \
         open(os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"), "rb") as al, \
         open(os.path.join(DOC_DIR, "credit_report_1.txt"), "rb") as cr:

        resp = client.post(
            "/applications",
            data={"full_name": "Test Applicant", "emirates_id": "784-1990-1234567-1",
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

    result = resp.json()
    app_id = result["application_id"]
    print("Submit status:", resp.status_code, "Decision:", result.get("decision"))

    # Confirm it's actually in the DB (not just an in-memory dict this time)
    get_resp = client.get(f"/applications/{app_id}")
    print("Get status:", get_resp.status_code, get_resp.json()["status"])

session = SessionLocal()
applicant_count = session.query(Applicant).count()
trace_count = session.query(AgentTrace).filter_by(application_id=app_id).count()
session.close()

print("Applicants persisted in DB:", applicant_count)
print("Agent trace rows persisted for this application:", trace_count)

assert resp.status_code == 200
assert get_resp.status_code == 200
assert applicant_count >= 1
assert trace_count > 0
print("\nPhase 7 database persistence OK.")
