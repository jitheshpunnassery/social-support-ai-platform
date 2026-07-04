"""Phase 8 smoke test: runs the full pipeline (now with LLM-backed resume
parsing, validation summaries, and decision explanations) and exercises the
/chat endpoint. Since Ollama is not running in this environment, this also
verifies the offline fallback text path works correctly end-to-end -- the
same code path used automatically if Ollama becomes unreachable in
production."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCAL_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local.db")
if os.path.exists(LOCAL_DB):
    os.remove(LOCAL_DB)

from fastapi.testclient import TestClient
from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from api.main import app
from agents.llm_client import llm_client

if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

print("LLM reachable (Ollama running)?", llm_client._probe())

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
    print("Decision reason (LLM or fallback):", result["decision_reason"])

    chat_resp = client.post("/chat", json={"application_id": result["application_id"],
                                             "message": "Why was my application decided this way?"})
    print("Chat reply:", chat_resp.json()["reply"][:200])

assert resp.status_code == 200
assert chat_resp.status_code == 200
assert len(result["decision_reason"]) > 0
print("\nPhase 8 Ollama integration (with offline fallback) OK.")
