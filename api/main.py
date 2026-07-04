import json
import logging
import os
import shutil
import tempfile
import time
import uuid

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from agents.orchestrator import run_application, LANGGRAPH_AVAILABLE
from agents.llm_client import llm_client
from api.schemas import ApplicationFormIn, ApplicationResult, ChatMessageIn, ChatMessageOut
from db.database import get_db, init_db
from db.models import Applicant, Application, Document, ApplicationStatus
from db.mongo_store import mongo_store
from db.vector_store import vector_store
from db.graph_store import graph_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Social Support AI Workflow", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Seed a couple of policy snippets into the vector store on startup so the
# chatbot has something grounded to retrieve (RAG demo).
POLICY_SNIPPETS = [
    ("policy_income_threshold", "Applicants with household per-capita monthly income below AED 1500 "
                                  "are generally eligible for direct financial support."),
    ("policy_enablement", "Applicants who are employable but under-skilled are offered economic "
                            "enablement support such as training, upskilling, and job matching, "
                            "regardless of the financial-support decision."),
    ("policy_review", "Any application with unresolved document inconsistencies (e.g. mismatched "
                        "name or expired Emirates ID) is routed to a human case officer before a "
                        "final decision is issued."),
]


@app.on_event("startup")
def startup():
    init_db()
    for pid, text in POLICY_SNIPPETS:
        vector_store.upsert(pid, text, {"text": text})
    logger.info("Startup complete. LangGraph available: %s", LANGGRAPH_AVAILABLE)


@app.get("/health")
def health():
    return {"status": "ok", "langgraph": LANGGRAPH_AVAILABLE}


def _read_upload(upload: UploadFile):
    suffix = os.path.splitext(upload.filename)[1].lower()
    content = upload.file.read()
    if suffix in (".xlsx", ".xls"):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(content)
        tmp.close()
        return tmp.name  # path, consumed by pandas.read_excel downstream
    if suffix == ".json":
        try:
            return json.loads(content.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return content.decode("utf-8", errors="ignore")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        # binary (image/pdf) - not decoded here; a production build would
        # route these through pdfplumber/pytesseract/vision-LLM extraction.
        return content


@app.post("/applications", response_model=ApplicationResult)
async def submit_application(
    full_name: str = Form(...),
    emirates_id: str = Form(...),
    date_of_birth: str = Form(None),
    nationality: str = Form("UAE"),
    phone: str = Form(None),
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
    db: Session = Depends(get_db),
):
    application_id = str(uuid.uuid4())

    applicant = db.query(Applicant).filter_by(emirates_id=emirates_id).first()
    if not applicant:
        applicant = Applicant(
            emirates_id=emirates_id, full_name=full_name, date_of_birth=date_of_birth,
            nationality=nationality, phone=phone, address=address, family_size=family_size,
            employment_status=employment_status, monthly_income=monthly_income,
        )
        db.add(applicant)
        db.commit()
        db.refresh(applicant)

    application = Application(id=application_id, applicant_id=applicant.id, status=ApplicationStatus.RECEIVED)
    db.add(application)
    db.commit()

    raw_documents = {}
    uploads = {
        "bank_statement": bank_statement, "emirates_id": emirates_id_doc, "resume": resume,
        "assets_liabilities": assets_liabilities, "credit_report": credit_report,
    }
    for doc_type, upload in uploads.items():
        if upload is None:
            continue
        content = _read_upload(upload)
        raw_documents[doc_type] = content
        mongo_ref = mongo_store.save_raw_document(application_id, doc_type,
                                                    content if isinstance(content, (str, dict)) else str(content))
        db.add(Document(application_id=application_id, doc_type=doc_type,
                         file_name=upload.filename, mongo_ref=mongo_ref))
    db.commit()

    if address:
        graph_store.link_applicant_to_household(applicant.id, address, family_size)

    state = {
        "application_id": application_id,
        "form_data": {
            "full_name": full_name, "address": address, "family_size": family_size,
            "employment_status": employment_status, "monthly_income": monthly_income,
            "months_employed": months_employed,
        },
        "raw_documents": raw_documents,
        "db_session": db,
    }

    start = time.perf_counter()
    result_state = run_application(state)
    processing_seconds = round(time.perf_counter() - start, 3)

    application.status = ApplicationStatus(result_state.get("decision") if result_state.get("decision") in
                                            [s.value for s in ApplicationStatus] else "needs_human_review")
    application.extracted_data = result_state.get("extracted_data")
    application.validation_report = result_state.get("validation_report")
    application.eligibility_features = result_state.get("eligibility_features")
    application.ml_score = result_state.get("ml_score")
    application.decision = result_state.get("decision")
    application.decision_reason = result_state.get("decision_reason")
    application.enablement_recommendations = result_state.get("enablement_recommendations")
    application.processing_seconds = processing_seconds
    db.commit()

    return ApplicationResult(
        application_id=application_id,
        status=application.status.value,
        decision=result_state.get("decision"),
        decision_reason=result_state.get("decision_reason"),
        ml_score=result_state.get("ml_score"),
        top_factors=result_state.get("top_factors"),
        validation_report=result_state.get("validation_report"),
        enablement_recommendations=result_state.get("enablement_recommendations"),
        enablement_narrative=result_state.get("enablement_narrative"),
        processing_seconds=processing_seconds,
        trace=result_state.get("trace"),
    )


@app.get("/applications/{application_id}", response_model=ApplicationResult)
def get_application(application_id: str, db: Session = Depends(get_db)):
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResult(
        application_id=application.id,
        status=application.status.value,
        decision=application.decision,
        decision_reason=application.decision_reason,
        ml_score=application.ml_score,
        validation_report=application.validation_report,
        enablement_recommendations=application.enablement_recommendations,
        processing_seconds=application.processing_seconds,
    )


@app.post("/chat", response_model=ChatMessageOut)
def chat(payload: ChatMessageIn, db: Session = Depends(get_db)):
    """Interactive chatbot endpoint. Retrieves relevant policy snippets (RAG
    via Qdrant) and, if an application_id is supplied, its current status,
    then asks the local LLM to respond grounded in that context."""
    context_chunks = vector_store.search(payload.message, top_k=2)
    policy_context = "\n".join(c["payload"].get("text", "") for c in context_chunks)

    app_context = ""
    if payload.application_id:
        application = db.query(Application).filter_by(id=payload.application_id).first()
        if application:
            app_context = (f"Application status: {application.status.value}. "
                            f"Decision: {application.decision}. Reason: {application.decision_reason}.")

    reply = llm_client.chat(
        "You are a helpful, empathetic assistant for a government social support department. "
        "Answer using the provided policy context and application context when relevant. "
        "Be concise and clear.",
        f"Policy context:\n{policy_context}\n\nApplication context:\n{app_context}\n\n"
        f"Applicant question: {payload.message}",
    )
    return ChatMessageOut(reply=reply)
