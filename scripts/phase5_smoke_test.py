"""Phase 5 smoke test: runs a full synthetic application through the
LangGraph-orchestrated pipeline (extraction -> validation -> eligibility ->
decision) and prints the resulting trace and decision."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from data.synthetic_data_generator import generate_applicants, generate_sample_documents, OUT_DIR, DOC_DIR
from agents.orchestrator import run_application, LANGGRAPH_AVAILABLE

if not os.path.exists(os.path.join(OUT_DIR, "applicants.csv")):
    generate_applicants(2000)
if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)
if not os.path.exists(settings.MODEL_PATH):
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "ml",
                                                   "train_eligibility_model.py")], check=True)

with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
    emirates_id = json.load(f)
with open(os.path.join(DOC_DIR, "bank_statement_1.txt")) as f:
    bank_statement = f.read()
with open(os.path.join(DOC_DIR, "resume_1.txt")) as f:
    resume = f.read()
with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
    credit_report = f.read()

state = {
    "form_data": {
        "full_name": emirates_id["name_en"], "address": "123 Sheikh Zayed Road, Dubai",
        "family_size": 4, "employment_status": "unemployed", "monthly_income": 1200, "months_employed": 0,
    },
    "raw_documents": {
        "bank_statement": bank_statement, "emirates_id": emirates_id, "resume": resume,
        "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"),
        "credit_report": credit_report,
    },
}

print(f"LangGraph available: {LANGGRAPH_AVAILABLE}\n")
result = run_application(state)

print("=== TRACE ===")
for step in result["trace"]:
    print(f"[{step['agent']}] {step['type']}: {step['content']}")

print("\nDecision:", result["decision"])
print("Reason:", result["decision_reason"])
print("Processing time (s):", result["processing_seconds"])

assert result["decision"] in {"approved", "soft_declined", "needs_human_review"}
print("\nPhase 5 orchestrator OK.")
