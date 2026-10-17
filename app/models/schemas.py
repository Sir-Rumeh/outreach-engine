from pydantic import BaseModel
from typing import Optional

class LeadItem(BaseModel):
    Name: str = "Founder"
    Company: str = "Your Company"
    Email: str = ""
    Channel: str = "LinkedIn"
    ProfileURL: str = "#"
    Focus: str = "React and Next.js development"

class EngineStateResponse(BaseModel):
    running: bool
    status: str
    progress: int
    total: int