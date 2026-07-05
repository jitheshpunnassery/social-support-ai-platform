"""Tests the new PDF/DOC/DOCX ingestion path: raw text extraction via
agents/document_readers.py, and end-to-end extraction via
DataExtractionAgent using PDF/DOCX-sourced documents instead of .txt/.json."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.synthetic_data_generator import DOC_DIR
from agents.document_readers import extract_text_from_pdf, extract_text_from_docx, extract_text_from_doc
from agents.data_extraction_agent import DataExtractionAgent

FIXTURES_DIR = os.path.join(DOC_DIR, "format_fixtures")


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    if not os.path.isdir(FIXTURES_DIR) or not os.listdir(FIXTURES_DIR):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts",
                                                        "generate_pdf_docx_fixtures.py")], check=True)


def test_pdf_text_extraction_bank_statement():
    text = extract_text_from_pdf(os.path.join(FIXTURES_DIR, "bank_statement_1.pdf"))
    assert "BANK STATEMENT" in text
    assert "BALANCE" in text


def test_docx_text_extraction_resume():
    text = extract_text_from_docx(os.path.join(FIXTURES_DIR, "resume_1.docx"))
    assert "RESUME" in text
    assert "Skills:" in text


def test_legacy_doc_extraction_via_libreoffice_conversion():
    text = extract_text_from_doc(os.path.join(FIXTURES_DIR, "resume_1.doc"))
    assert "RESUME" in text
    assert "Skills:" in text


def test_extraction_agent_handles_pdf_bank_statement():
    state = {"raw_documents": {
        "bank_statement": extract_text_from_pdf(os.path.join(FIXTURES_DIR, "bank_statement_1.pdf")),
    }}
    result = DataExtractionAgent().run(state)
    assert result["extracted_data"]["bank_statement"]["months_covered"] > 0


def test_extraction_agent_handles_docx_resume():
    state = {"raw_documents": {
        "resume": extract_text_from_docx(os.path.join(FIXTURES_DIR, "resume_1.docx")),
    }}
    result = DataExtractionAgent().run(state)
    assert len(result["extracted_data"]["resume"]["skills"]) > 0


def test_extraction_agent_handles_pdf_credit_report():
    state = {"raw_documents": {
        "credit_report": extract_text_from_pdf(os.path.join(FIXTURES_DIR, "credit_report_1.pdf")),
    }}
    result = DataExtractionAgent().run(state)
    assert result["extracted_data"]["credit_report"]["credit_score"] is not None


def test_extraction_agent_handles_text_formatted_emirates_id():
    """Emirates ID supplied as PDF/DOCX text (not the JSON fixture) should
    still be parsed correctly via the new regex fallback."""
    with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
        original = json.load(f)

    text = extract_text_from_pdf(os.path.join(FIXTURES_DIR, "emirates_id_1.pdf"))
    state = {"raw_documents": {"emirates_id": text}}
    result = DataExtractionAgent().run(state)
    parsed = result["extracted_data"]["emirates_id"]

    assert parsed["id_number"] == original["id_number"]
    assert parsed["name_en"] == original["name_en"]
