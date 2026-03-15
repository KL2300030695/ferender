from pydantic import BaseModel
from typing import List

class SessionData(BaseModel):
    resilience_score: int
    empathy_level: str
    messages_count: int
    duration_seconds: int
    emotion_log: List[str]
