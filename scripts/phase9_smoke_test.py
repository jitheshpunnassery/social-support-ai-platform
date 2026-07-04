"""Phase 9 smoke test: submits an unemployed applicant with resume skills
and confirms the Economic Enablement Agent's recommendations come back
through the full API response (and are persisted to the DB record)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.db")
if os.path.exists(LOCAL_DB):
    os.remove(LOCAL_DB)

from fastapi.testclient import TestClient
from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from api.main import app

if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

with TestClient(app) as client:
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

    print("Enablement recommendations:", result.get("enablement_recommendations"))
    print("Enablement narrative:", result.get("enablement_narrative"))

    get_resp = client.get(f"/applications/{app_id}")
    persisted = get_resp.json()
    print("Persisted enablement recommendations:", persisted.get("enablement_recommendations"))

assert resp.status_code == 200
assert result.get("enablement_recommendations") is not None
assert len(result["enablement_recommendations"]) > 0
assert persisted.get("enablement_recommendations") == result.get("enablement_recommendations")
print("\nPhase 9 enablement agent OK.")
