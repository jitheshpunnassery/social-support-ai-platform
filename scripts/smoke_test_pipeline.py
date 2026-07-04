"""Runs one synthetic application through the full agent pipeline without
requiring any external services (Postgres/Mongo/Qdrant/Neo4j/Ollama) to be
running -- useful for CI and for quickly sanity-checking the orchestrator."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import run_application, LANGGRAPH_AVAILABLE

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE, "data", "synthetic", "sample_documents")

with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
    emirates_id = json.load(f)
with open(os.path.join(DOC_DIR, "bank_statement_1.txt")) as f:
    bank_statement = f.read()
with open(os.path.join(DOC_DIR, "resume_1.txt")) as f:
    resume = f.read()
with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
    credit_report = f.read()

state = {
    "application_id": "TEST-0001",
    "form_data": {
        "full_name": emirates_id["name_en"],
        "address": "123 Sheikh Zayed Road, Dubai",
        "family_size": 4,
        "employment_status": "unemployed",
        "monthly_income": 1200,
        "months_employed": 0,
    },
    "raw_documents": {
        "bank_statement": bank_statement,
        "emirates_id": emirates_id,
        "resume": resume,
        "assets_liabilities": os.path.join(DOC_DIR, "assets_liabilities_1.xlsx"),
        "credit_report": credit_report,
    },
}

print(f"LangGraph available: {LANGGRAPH_AVAILABLE}\n")
result = run_application(state)

print("=== TRACE ===")
for step in result["trace"]:
    print(f"[{step['agent']}] {step['type']}: {step['content']}")

print("\n=== RESULT ===")
print("Eligibility score:", result.get("ml_score"))
print("Top factors:", result.get("top_factors"))
print("Decision:", result.get("decision"))
print("Reason:", result.get("decision_reason"))
print("Validation:", result.get("validation_report"))
print("Enablement:", result.get("enablement_recommendations"))
print("Processing time (s):", result.get("processing_seconds"))
