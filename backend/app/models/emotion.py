from pydantic import BaseModel

class EmotionRequest(BaseModel):
    image: str # base64 encoded image
