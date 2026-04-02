from functools import lru_cache
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import get_connection
from ..rag.llm_rca_generator import RCAGenerator

router = APIRouter()


@lru_cache(maxsize=1)
def get_rca_generator() -> RCAGenerator:
    return RCAGenerator()


class ChatRequest(BaseModel):
    question: str
    rca_context: str
    incident_id: Optional[int] = None


class ImpactRequest(BaseModel):
    rca_context: str


@router.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    try:
        rca_generator = get_rca_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    df = pd.read_excel(file.file)
    text = df.to_string()

    rca = rca_generator.generate_rca(
        incident=text,
        similar_incidents="",
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO incident_rca (incident_file, rca_report, impact_level)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (file.filename, rca, "unknown"),
    )

    incident_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {"incident_id": incident_id, "rca_report": rca}


@router.post("/chat")
async def chat_with_rca(data: ChatRequest):
    try:
        rca_generator = get_rca_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt = f"""
You are Glow, an expert incident management assistant.

Here is the RCA report:

{data.rca_context}

User question:
{data.question}

Answer clearly and helpfully.
Use concise headings and bullet points where appropriate.
"""

    response = rca_generator.llm.invoke(prompt)
    answer = response.content

    if data.incident_id is not None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO incident_chat (incident_id, question, answer)
            VALUES (%s, %s, %s)
            """,
            (data.incident_id, data.question, answer),
        )
        conn.commit()
        cursor.close()
        conn.close()

    return {"answer": answer}


@router.post("/impact-classification")
async def impact_classification(data: ImpactRequest):
    try:
        rca_generator = get_rca_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt = f"""
You are an SRE incident analysis expert.

Based on the RCA below classify the incident impact.

Return:

Severity (Critical / High / Medium / Low)
Services Impacted
Regions Impacted
Estimated Users Impacted

RCA:
{data.rca_context}
"""

    response = rca_generator.llm.invoke(prompt)

    return {"impact": response.content}


@router.get("/past-incidents")
async def past_incidents():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, incident_file, created_at
        FROM incident_rca
        ORDER BY created_at DESC
        LIMIT 50
        """
    )

    rows = cursor.fetchall()
    incidents = [
        {"id": row[0], "incident_file": row[1], "created_at": str(row[2])}
        for row in rows
    ]

    cursor.close()
    conn.close()

    return incidents


@router.get("/incident/{incident_id}")
async def incident_details(incident_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, incident_file, rca_report, created_at
        FROM incident_rca
        WHERE id = %s
        """,
        (incident_id,),
    )

    incident = cursor.fetchone()
    if not incident:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Incident not found")

    cursor.execute(
        """
        SELECT question, answer, created_at
        FROM incident_chat
        WHERE incident_id = %s
        ORDER BY created_at ASC
        """,
        (incident_id,),
    )
    chat_rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "id": incident[0],
        "incident_file": incident[1],
        "rca_report": incident[2],
        "created_at": str(incident[3]),
        "chat_history": [
            {"question": row[0], "answer": row[1], "created_at": str(row[2])}
            for row in chat_rows
        ],
    }