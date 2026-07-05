import enum
import uuid
from datetime import datetime

from sqlalchemy import (Column, String, Float, Integer, Boolean, DateTime,
                         ForeignKey, Enum, Text, JSON)
from sqlalchemy.orm import relationship

from db.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class ApplicationStatus(str, enum.Enum):
    RECEIVED = "received"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    ASSESSING = "assessing"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    APPROVED = "approved"
    SOFT_DECLINED = "soft_declined"
    ENABLEMENT_RECOMMENDED = "enablement_recommended"


class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(String, primary_key=True, default=gen_id)
    emirates_id = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    nationality = Column(String, nullable=False)
    marital_status = Column(String, nullable=False)
    mobile_number = Column(String, nullable=False)
    email = Column(String, nullable=False)
    address = Column(String, nullable=False)              # Current residential address
    emirate = Column(String, nullable=False)                # Emirate of residence
    residency_status = Column(String, nullable=False)
    family_size = Column(Integer, default=1)
    employment_status = Column(String)
    monthly_income = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="applicant")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=gen_id)
    applicant_id = Column(String, ForeignKey("applicants.id"))
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.RECEIVED)

    # Extracted / normalized features used at decision time
    extracted_data = Column(JSON, default=dict)          # raw multimodal extraction results
    validation_report = Column(JSON, default=dict)        # cross-document consistency findings
    eligibility_features = Column(JSON, default=dict)     # engineered features fed to ML model
    ml_score = Column(Float, nullable=True)                # model probability of eligibility
    decision = Column(String, nullable=True)                # approved / soft_declined / needs_review
    decision_reason = Column(Text, nullable=True)
    enablement_recommendations = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    processing_seconds = Column(Float, nullable=True)

    applicant = relationship("Applicant", back_populates="applications")
    documents = relationship("Document", back_populates="application")
    agent_traces = relationship("AgentTrace", back_populates="application")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_id)
    application_id = Column(String, ForeignKey("applications.id"))
    doc_type = Column(String)          # bank_statement | emirates_id | resume | assets_liabilities | credit_report
    file_name = Column(String)
    mongo_ref = Column(String)          # pointer to raw content/blob stored in MongoDB
    extracted_fields = Column(JSON, default=dict)
    ocr_confidence = Column(Float, nullable=True)

    application = relationship("Application", back_populates="documents")


class AgentTrace(Base):
    """Lightweight local audit trail (mirrors what Langfuse captures) so the
    reasoning chain is inspectable directly from Postgres/SQLite as well."""
    __tablename__ = "agent_traces"

    id = Column(String, primary_key=True, default=gen_id)
    application_id = Column(String, ForeignKey("applications.id"))
    agent_name = Column(String)
    step = Column(String)               # thought | action | observation | decision
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="agent_traces")
