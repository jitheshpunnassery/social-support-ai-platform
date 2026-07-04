"""Phase 6 smoke test: exercises the FastAPI backend end-to-end via
TestClient (no real HTTP server, no database) to confirm the API wraps the
Phase 5 orchestrator correctly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from api.main import app

if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

client = TestClient(app)

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

print("Submit status:", resp.status_code)
result = resp.json()
print("Decision:", result.get("decision"))
app_id = result["application_id"]

get_resp = client.get(f"/applications/{app_id}")
print("Get status:", get_resp.status_code, get_resp.json()["status"])

assert resp.status_code == 200
assert get_resp.status_code == 200
print("\nPhase 6 API OK.")
