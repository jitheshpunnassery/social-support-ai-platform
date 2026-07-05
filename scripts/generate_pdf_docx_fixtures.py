"""
Generates PDF, DOC, and DOCX versions of the existing plain-text sample
documents (bank statement, resume, credit report) plus a text-formatted
Emirates ID document, so the new PDF/DOC/DOCX ingestion path can be tested
against realistic multi-format input -- not just the .txt/.json fixtures
used in earlier phases.

Requires LibreOffice ('soffice') on PATH for .docx -> .pdf / .docx -> .doc
conversion (the same dependency documented for legacy .doc support).

Run: python scripts/generate_pdf_docx_fixtures.py
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docx import Document
from data.synthetic_data_generator import DOC_DIR

FIXTURES_DIR = os.path.join(DOC_DIR, "format_fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)


def _text_to_docx(text: str, out_path: str):
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(out_path)


def _convert(src_docx: str, target_format: str):
    subprocess.run(
        ["soffice", "--headless", "--convert-to", target_format, "--outdir", FIXTURES_DIR, src_docx],
        check=True, capture_output=True, timeout=60,
    )


def main():
    with open(os.path.join(DOC_DIR, "bank_statement_1.txt")) as f:
        bank_statement_text = f.read()
    with open(os.path.join(DOC_DIR, "resume_1.txt")) as f:
        resume_text = f.read()
    with open(os.path.join(DOC_DIR, "credit_report_1.txt")) as f:
        credit_report_text = f.read()
    with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
        eid = json.load(f)

    emirates_id_text = "\n".join([
        f"Name (EN): {eid['name_en']}",
        f"ID Number: {eid['id_number']}",
        f"Nationality: {eid['nationality']}",
        f"Date of Birth: {eid['date_of_birth']}",
        f"Expiry Date: {eid['expiry_date']}",
    ])

    fixtures = {
        "bank_statement_1": bank_statement_text,
        "resume_1": resume_text,
        "credit_report_1": credit_report_text,
        "emirates_id_1": emirates_id_text,
    }

    for name, text in fixtures.items():
        docx_path = os.path.join(FIXTURES_DIR, f"{name}.docx")
        _text_to_docx(text, docx_path)
        _convert(docx_path, "pdf")
        print(f"Generated {name}.docx and {name}.pdf")

    # Also produce one legacy .doc fixture (round-trip via LibreOffice) to
    # exercise the .doc -> .docx conversion fallback path.
    _convert(os.path.join(FIXTURES_DIR, "resume_1.docx"), "doc")
    print("Generated resume_1.doc (legacy format)")


if __name__ == "__main__":
    main()
