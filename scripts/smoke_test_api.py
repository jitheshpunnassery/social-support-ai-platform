import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE, "data", "synthetic", "sample_documents")

with TestClient(app) as client:
    print("Health:", client.get("/health").json())

    with open(os.path.join(DOC_DIR, "bank_statement_1.txt"), "rb") as bs, \
         open(os.path.join(DOC_DIR, "emirates_id_1.json"), "rb") as eid, \
         open(os.path.join(DOC_DIR, "resume_1.txt"), "rb") as res, \
         open(os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"), "rb") as al, \
         open(os.path.join(DOC_DIR, "credit_report_1.txt"), "rb") as cr:

        resp = client.post(
            "/applications",
            data={
                "full_name": "Test Applicant", "emirates_id": "784-1990-1234567-1",
                "family_size": 5, "employment_status": "unemployed",
                "monthly_income": 900, "address": "123 Sheikh Zayed Road, Dubai",
            },
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
    print("Score:", result.get("ml_score"))
    print("Application ID:", result.get("application_id"))

    app_id = result.get("application_id")
    get_resp = client.get(f"/applications/{app_id}")
    print("Get status:", get_resp.status_code, get_resp.json().get("status"))

    chat_resp = client.post("/chat", json={"application_id": app_id, "message": "Why was my application decided this way?"})
    print("Chat reply:", chat_resp.json()["reply"][:200])
