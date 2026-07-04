"""
FastAPI backend.

NOTE: This phase stores results in a simple in-process dict
(`_APPLICATIONS_DB`) so the API + Streamlit UI can be demonstrated without
any database. Phase 7 replaces this dict with real PostgreSQL + MongoDB
persistence behind the exact same endpoint contracts, so the frontend built
in this phase doesn't need to change.
"""
import json
import logging
import os
import tempfile
import time
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agents.orchestrator import run_application, LANGGRAPH_AVAILABLE
from api.schemas import ApplicationResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Social Support AI Workflow", version="0.6.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory store, replaced by PostgreSQL/MongoDB in Phase 7.
_APPLICATIONS_DB: dict = {}


@app.get("/health")
def health():
    return {"status": "ok", "langgraph": LANGGRAPH_AVAILABLE, "storage": "in-memory (Phase 6)"}


def _read_upload(upload: UploadFile):
    suffix = os.path.splitext(upload.filename)[1].lower()
    content = upload.file.read()
    if suffix in (".xlsx", ".xls"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(content)
        tmp.close()
        return tmp.name
    if suffix == ".json":
        try:
            return json.loads(content.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return content.decode("utf-8", errors="ignore")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content


@app.post("/applications", response_model=ApplicationResult)
async def submit_application(
    full_name: str = Form(...),
    emirates_id: str = Form(...),
    address: str = Form(None),
    family_size: int = Form(1),
    employment_status: str = Form("unemployed"),
    monthly_income: float = Form(0.0),
    months_employed: int = Form(0),
    bank_statement: UploadFile = File(None),
    emirates_id_doc: UploadFile = File(None),
    resume: UploadFile = File(None),
    assets_liabilities: UploadFile = File(None),
    credit_report: UploadFile = File(None),
):
    application_id = str(uuid.uuid4())

    raw_documents = {}
    uploads = {
        "bank_statement": bank_statement, "emirates_id": emirates_id_doc, "resume": resume,
        "assets_liabilities": assets_liabilities, "credit_report": credit_report,
    }
    for doc_type, upload in uploads.items():
        if upload is not None:
            raw_documents[doc_type] = _read_upload(upload)

    state = {
        "form_data": {
            "full_name": full_name, "address": address, "family_size": family_size,
            "employment_status": employment_status, "monthly_income": monthly_income,
            "months_employed": months_employed,
        },
        "raw_documents": raw_documents,
    }

    start = time.perf_counter()
    result_state = run_application(state)
    processing_seconds = round(time.perf_counter() - start, 3)

    record = {
        "application_id": application_id,
        "status": result_state.get("decision", "needs_human_review"),
        "decision": result_state.get("decision"),
        "decision_reason": result_state.get("decision_reason"),
        "ml_score": result_state.get("ml_score"),
        "top_factors": result_state.get("top_factors"),
        "validation_report": result_state.get("validation_report"),
        "processing_seconds": processing_seconds,
        "trace": result_state.get("trace"),
    }
    _APPLICATIONS_DB[application_id] = record  # Phase 7 replaces this with a DB write
    return ApplicationResult(**record)


@app.get("/applications/{application_id}", response_model=ApplicationResult)
def get_application(application_id: str):
    record = _APPLICATIONS_DB.get(application_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResult(**record)
