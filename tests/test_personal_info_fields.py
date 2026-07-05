"""Verifies the expanded personal information fields (Date of Birth,
Gender, Nationality, Marital Status, Mobile Number, Email Address,
Current Residential Address, Emirate, Residency Status) are genuinely
required by the API -- not just documented as required -- and that the
new fields are functionally used by the Data Validation Agent (DOB and
nationality cross-checks against the Emirates ID document)."""
import json
import os

import pytest
from fastapi.testclient import TestClient

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(BASE, "data", "synthetic", "sample_documents")

REQUIRED_FIELDS = {
    "full_name": "Test Applicant",
    "emirates_id": "784-1990-1234567-1",
    "date_of_birth": "1990-05-15",
    "gender": "Male",
    "nationality": "UAE",
    "marital_status": "Single",
    "mobile_number": "+971501234567",
    "email": "test.applicant@example.com",
    "address": "123 Sheikh Zayed Road, Dubai",
    "emirate": "Dubai",
    "residency_status": "UAE National",
}


@pytest.fixture(scope="module")
def client():
    from data.synthetic_data_generator import generate_sample_documents
    if not os.path.isdir(DOC_DIR) or not os.listdir(DOC_DIR):
        generate_sample_documents(5)

    from api.main import app
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("missing_field", list(REQUIRED_FIELDS.keys()))
def test_each_personal_info_field_is_mandatory(client, missing_field):
    """Omitting any single required personal-information field should be
    rejected by FastAPI's own validation (422), before the pipeline even
    runs -- proving these fields are enforced server-side, not just
    suggested by the UI."""
    data = {k: v for k, v in REQUIRED_FIELDS.items() if k != missing_field}
    resp = client.post("/applications", data=data)
    assert resp.status_code == 422, (
        f"Expected 422 when '{missing_field}' is omitted, got {resp.status_code}: {resp.text}"
    )


def test_all_fields_present_succeeds(client):
    resp = client.post("/applications", data=REQUIRED_FIELDS)
    assert resp.status_code == 200
    result = resp.json()
    assert result["decision"] in {"approved", "soft_declined", "needs_human_review"}


def test_date_of_birth_mismatch_flagged(client):
    """The applicant's self-reported DOB is deliberately different from
    the DOB on the (JSON-fixture) Emirates ID document -- the validation
    agent should catch this using the newly-added cross-check."""
    with open(os.path.join(DOC_DIR, "emirates_id_1.json")) as f:
        eid = json.load(f)

    data = dict(REQUIRED_FIELDS)
    data["full_name"] = eid["name_en"]  # keep name matching so only DOB differs
    data["nationality"] = eid["nationality"]
    data["date_of_birth"] = "1975-01-01"  # deliberately wrong vs. the fixture

    with open(os.path.join(DOC_DIR, "emirates_id_1.json"), "rb") as eid_file:
        resp = client.post(
            "/applications", data=data,
            files={"emirates_id_doc": ("emirates_id_1.json", eid_file, "application/json")},
        )

    assert resp.status_code == 200
    result = resp.json()
    flagged_fields = [f["field"] for f in result["validation_report"]["flags"]]
    assert "date_of_birth" in flagged_fields
