import json
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import get_connection
from .attendee_extractor import extract_from_excel, extract_from_docx, extract_mir_metadata
from .docx_builder import build_mir_docx
from .mir_generator import MIRGenerator

router = APIRouter(prefix="/mir", tags=["MIR"])


@lru_cache(maxsize=1)
def get_mir_generator() -> MIRGenerator:
    return MIRGenerator()


# ── Stakeholder models ────────────────────────────────────────────────────────

class StakeholderConfig(BaseModel):
    cc_always: list[str]        # always CC these addresses
    sco_dl: str                 # DL added when is_sco=True
    non_sco_cc: list[str]       # additional CC for non-SCO PRBs


# ── /mir/parse-doc ────────────────────────────────────────────────────────────

@router.post("/parse-doc")
async def parse_mir_doc(file: UploadFile = File(...)):
    """
    Parse an uploaded MIR Word document (.docx) and return:
    - metadata (inc, prb, title, description, resolution, business_impact)
    - existing attendees list
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    file_bytes = await file.read()
    metadata = extract_mir_metadata(file_bytes)
    attendees = extract_from_docx(file_bytes)
    return {"metadata": metadata, "attendees": attendees}


# ── /mir/parse-excel ─────────────────────────────────────────────────────────

@router.post("/parse-excel")
async def parse_whiteboard(file: UploadFile = File(...)):
    """
    Parse whiteboard Excel and extract Key Participants.
    Returns list of {team, emails[]} objects.
    """
    file_bytes = await file.read()
    participants = extract_from_excel(file_bytes)
    return {"participants": participants}


# ── /mir/generate ─────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_mir(
    inc_number: str = Form(...),
    prb_number: str = Form(...),
    ci: str = Form(""),
    title: str = Form(...),
    description: str = Form(...),
    resolution: str = Form(...),
    business_impact: str = Form(""),
    is_sco: bool = Form(False),
    inc_opened: str = Form(""),
    inc_resolved: str = Form(""),
    duration_degraded: str = Form(""),
    whiteboard_file: Optional[UploadFile] = File(None),
):
    """
    Main generation endpoint. Returns:
    - impact_heading
    - questions (Q1-Q10)
    - attendees (from whiteboard if uploaded)
    - meeting_subject
    - meeting_email_body
    - to_list, cc_list
    """
    try:
        gen = get_mir_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Generate heading and questions in sequence
    impact_heading = gen.generate_impact_heading(description, resolution)
    questions = gen.generate_questions(title, description, resolution, business_impact)

    # Extract attendees from whiteboard
    attendees = []
    if whiteboard_file:
        wb_bytes = await whiteboard_file.read()
        attendees = extract_from_excel(wb_bytes)

    # Build TO list from whiteboard Key Participants (all emails)
    to_emails = []
    for entry in attendees:
        to_emails.extend(entry.get("emails", []))

    # Build CC list from saved stakeholders
    cc_emails = []
    try:
        stakeholders = _load_stakeholders()
        cc_emails = list(stakeholders.get("cc_always", []))
        if is_sco and stakeholders.get("sco_dl"):
            cc_emails.append(stakeholders["sco_dl"])
        elif not is_sco:
            cc_emails.extend(stakeholders.get("non_sco_cc", []))
    except Exception:
        pass  # No stakeholders configured yet

    # Generate meeting email body
    email_body = gen.generate_meeting_email(
        inc_number, prb_number, title, impact_heading, questions
    )

    meeting_subject = f"MIR Call – {inc_number} – {impact_heading}"

    return {
        "inc_number": inc_number,
        "prb_number": prb_number,
        "ci": ci,
        "title": title,
        "description": description,
        "resolution": resolution,
        "business_impact": business_impact,
        "inc_opened": inc_opened,
        "inc_resolved": inc_resolved,
        "duration_degraded": duration_degraded,
        "impact_heading": impact_heading,
        "questions": questions,
        "attendees": attendees,
        "to_list": to_emails,
        "cc_list": cc_emails,
        "meeting_subject": meeting_subject,
        "email_body": email_body,
    }


# ── /mir/download ─────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    inc_number: str
    prb_number: str
    ci: Optional[str] = ""
    title: str
    description: str
    resolution: str
    business_impact: Optional[str] = ""
    inc_opened: Optional[str] = ""
    inc_resolved: Optional[str] = ""
    duration_degraded: Optional[str] = ""
    impact_heading: str
    questions: list[str]
    attendees: list[dict]
    root_cause_summary: Optional[str] = ""
    capa: Optional[str] = ""


@router.post("/download")
async def download_mir_docx(data: DownloadRequest):
    """Return a filled MIR .docx file for download."""
    docx_bytes = build_mir_docx(data.model_dump())
    filename = f"MIR_{data.inc_number.replace(' ', '_')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── /mir/timeline-check ───────────────────────────────────────────────────────

@router.post("/timeline-check")
async def check_timeline(file: UploadFile = File(...)):
    """
    Accept a screenshot/image of the INC timeline and review it
    against MIR standards. Returns pass/fail checklist + gap flags.
    """
    try:
        gen = get_mir_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    image_bytes = await file.read()
    mime_type = file.content_type or "image/png"

    result = gen.review_timeline_image(image_bytes, mime_type)
    return result


# ── /mir/stakeholders ─────────────────────────────────────────────────────────

def _load_stakeholders() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT config_json FROM mir_stakeholders ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return {"cc_always": [], "sco_dl": "", "non_sco_cc": []}
    return json.loads(row[0])


@router.get("/stakeholders")
async def get_stakeholders():
    """Return saved stakeholder configuration."""
    return _load_stakeholders()


@router.post("/stakeholders")
async def save_stakeholders(config: StakeholderConfig):
    """Save stakeholder configuration (CC lists, SCO DL)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mir_stakeholders (config_json) VALUES (%s)",
        (json.dumps(config.model_dump()),),
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"saved": True}
