"""Phase 2 smoke test: generates synthetic sample documents (if not already
present) and runs the Data Extraction Agent against them end-to-end."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.synthetic_data_generator import generate_sample_documents, DOC_DIR
from agents.data_extraction_agent import DataExtractionAgent

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

state = {
    "raw_documents": {
        "bank_statement": bank_statement,
        "emirates_id": emirates_id,
        "resume": resume,
        "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"),
        "credit_report": credit_report,
    }
}

result = DataExtractionAgent().run(state)

print("=== Extracted Data ===")
print(json.dumps(result["extracted_data"], indent=2, default=str))

assert "bank_statement" in result["extracted_data"]
assert "assets_liabilities" in result["extracted_data"]
assert result["extracted_data"]["assets_liabilities"]["total_assets"] >= 0
assert len(result["trace"]) > 0
print("\nPhase 2 extraction agent OK.")
