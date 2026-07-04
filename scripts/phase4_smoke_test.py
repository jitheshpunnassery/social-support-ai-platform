"""Phase 4 smoke test: generates the synthetic applicants table (if
missing), trains the eligibility model (if missing), then runs the
Eligibility Agent against a sample applicant built from Phase 2's extracted
document data."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from data.synthetic_data_generator import generate_applicants, generate_sample_documents, OUT_DIR, DOC_DIR
from agents.data_extraction_agent import DataExtractionAgent
from agents.eligibility_agent import EligibilityAgent

if not os.path.exists(os.path.join(OUT_DIR, "applicants.csv")):
    generate_applicants(2000)
if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

if not os.path.exists(settings.MODEL_PATH):
    print("Training eligibility model (first run only)...")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "ml",
                                                   "train_eligibility_model.py")], check=True)

with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
    credit_report = f.read()

state = {
    "form_data": {
        "family_size": 5, "employment_status": "unemployed", "monthly_income": 900,
        "months_employed": 0, "total_assets": 5000, "total_liabilities": 20000,
    },
    "raw_documents": {"credit_report": credit_report,
                       "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx")},
}
state = DataExtractionAgent().run(state)
state = EligibilityAgent().run(state)

print("Eligibility features:", json.dumps(state["eligibility_features"], indent=2))
print("ML score:", state["ml_score"])
print("Top factors:", state["top_factors"])

assert 0.0 <= state["ml_score"] <= 1.0
print("\nPhase 4 eligibility agent OK.")
