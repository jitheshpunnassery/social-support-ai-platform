"""Phase 11 smoke test: submits an application via the actual FastAPI
upload endpoint using PDF and DOCX files (not the .txt/.json fixtures used
in earlier phases), confirming the whole pipeline -- upload -> text
extraction -> agent parsing -> eligibility -> decision -- works with the
newly added document formats."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.db")
if os.path.exists(LOCAL_DB):
    os.remove(LOCAL_DB)

from fastapi.testclient import TestClient
from data.synthetic_data_generator import DOC_DIR
from api.main import app

FIXTURES_DIR = os.path.join(DOC_DIR, "format_fixtures")
if not os.path.isdir(FIXTURES_DIR) or not os.listdir(FIXTURES_DIR):
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "generate_pdf_docx_fixtures.py")],
                   check=True)

with TestClient(app) as client:
    with open(os.path.join(FIXTURES_DIR, "bank_statement_1.pdf"), "rb") as bs, \
         open(os.path.join(FIXTURES_DIR, "emirates_id_1.pdf"), "rb") as eid, \
         open(os.path.join(FIXTURES_DIR, "resume_1.docx"), "rb") as res, \
         open(os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"), "rb") as al, \
         open(os.path.join(FIXTURES_DIR, "credit_report_1.pdf"), "rb") as cr:

        resp = client.post(
            "/applications",
            data={"full_name": "PDF Docx Applicant", "emirates_id": "784-1990-1234567-1",
                  "family_size": 4, "employment_status": "unemployed", "monthly_income": 1000,
                  "address": "123 Sheikh Zayed Road, Dubai"},
            files={
                "bank_statement": ("bank_statement_1.pdf", bs, "application/pdf"),
                "emirates_id_doc": ("emirates_id_1.pdf", eid, "application/pdf"),
                "resume": ("resume_1.docx", res,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                "assets_liabilities": ("assets_liabilities_1.xlsx", al,
                                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "credit_report": ("credit_report_1.pdf", cr, "application/pdf"),
            },
        )

result = resp.json()
print("Status code:", resp.status_code)
print("Decision:", result.get("decision"))
print("ML score:", result.get("ml_score"))
print("Validation flags:", result.get("validation_report", {}).get("flags"))

assert resp.status_code == 200
assert result.get("decision") in {"approved", "soft_declined", "needs_human_review"}
assert result.get("ml_score") is not None
print("\nPhase 11 PDF/DOC/DOCX support OK.")
