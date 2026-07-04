from typing import Optional
from pydantic import BaseModel


class ApplicationResult(BaseModel):
    application_id: str
    status: str
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    ml_score: Optional[float] = None
    top_factors: Optional[list] = None
    validation_report: Optional[dict] = None
    processing_seconds: Optional[float] = None
    trace: Optional[list] = None
