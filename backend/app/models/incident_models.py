from pydantic import BaseModel


class IncidentInput(BaseModel):

    title: str
    service: str
    error_logs: str
    timeline: str
    observations: str