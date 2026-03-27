from functools import lru_cache

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
        """,
        (file.filename, rca, "unknown"),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return {"rca_report": rca}


@router.post("/chat")
async def chat_with_rca(data: ChatRequest):
    try:
        rca_generator = get_rca_generator()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    prompt = f"""
You are an expert incident management assistant.

Here is the RCA report:

{data.rca_context}

User question:
{data.question}

Answer clearly and helpfully.
"""

    response = rca_generator.llm.invoke(prompt)

    return {"answer": response.content}


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
        LIMIT 10
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
