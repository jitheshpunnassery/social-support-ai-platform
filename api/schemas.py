from typing import Optional, Any
from pydantic import BaseModel, Field


class ApplicationFormIn(BaseModel):
    full_name: str
    emirates_id: str
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = "UAE"
    phone: Optional[str] = None
    address: Optional[str] = None
    family_size: int = 1
    employment_status: str = "unemployed"
    monthly_income: float = 0.0
    months_employed: int = 0


class ApplicationResult(BaseModel):
    application_id: str
    status: str
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    ml_score: Optional[float] = None
    top_factors: Optional[list] = None
    validation_report: Optional[dict] = None
    enablement_recommendations: Optional[list] = None
    enablement_narrative: Optional[str] = None
    processing_seconds: Optional[float] = None
    trace: Optional[list] = None


class ChatMessageIn(BaseModel):
    application_id: Optional[str] = None
    message: str


class ChatMessageOut(BaseModel):
    reply: str
