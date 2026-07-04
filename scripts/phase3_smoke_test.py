"""Phase 3 smoke test: runs extraction + validation together and confirms
both a clean case and a deliberately broken case (expired ID) are flagged
correctly."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from agents.data_extraction_agent import DataExtractionAgent
from agents.data_validation_agent import DataValidationAgent

if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
    generate_sample_documents(5)

with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
    emirates_id = json.load(f)
with open(os.path.join(DOC_DIR, "bank_statement_1.txt")) as f:
    bank_statement = f.read()
with open(os.path.join(DOC_DIR, "resume_1.txt")) as f:
    resume = f.read()
with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
    credit_report = f.read()

base_docs = {
    "bank_statement": bank_statement,
    "emirates_id": emirates_id,
    "resume": resume,
    "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"),
    "credit_report": credit_report,
}

# --- Case 1: clean, consistent application ---
state = {
    "form_data": {"full_name": emirates_id["name_en"], "address": "123 Random St", "monthly_income": 3000},
    "raw_documents": base_docs,
}
state = DataExtractionAgent().run(state)
state = DataValidationAgent().run(state)
print("Clean case severity:", state["validation_report"]["overall_severity"])
assert state["validation_report"]["overall_severity"] in ("none", "medium")

# --- Case 2: expired Emirates ID -> must force human review ---
broken_id = dict(emirates_id)
broken_id["expiry_date"] = "2020-01-01"
state2 = {
    "form_data": {"full_name": emirates_id["name_en"], "address": "123 Random St", "monthly_income": 3000},
    "raw_documents": {**base_docs, "emirates_id": broken_id},
}
state2 = DataExtractionAgent().run(state2)
state2 = DataValidationAgent().run(state2)
print("Expired-ID case severity:", state2["validation_report"]["overall_severity"])
print("Flags:", state2["validation_report"]["flags"])
assert state2["validation_report"]["requires_human_review"] is True

print("\nPhase 3 validation agent OK.")
