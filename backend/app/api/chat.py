from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import requests
import json
from app.models.chat import ChatRequest
from app.api.dependencies import get_current_user
from app.core.config import settings

router = APIRouter(tags=["chat"])

@router.post("/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    messages = [m.model_dump() for m in request.messages]
    
    user_name = current_user["first_name"] if current_user else "Friend"
    
    system_content = (
        "You are a world-class AI Wellness Companion. "
        "Your responses should be supportive, insightful, and concise. "
        f"You are speaking to {user_name}. "
        f"The user currently appears to feel: {request.current_emotion}. "
        "Tailor your response to this emotion without being overly clinical. Use markdown."
    )
    
    if messages[0]["role"] == "system":
        messages[0]["content"] = system_content
    else:
        messages.insert(0, {"role": "system", "content": system_content})

    async def stream_generator():
        try:
            payload = {
                "model": settings.LLAMA_MODEL_NAME,
                "messages": messages,
                "stream": True
            }
            with requests.post(settings.OLLAMA_URL, json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                        if chunk.get("done"):
                            break
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(stream_generator(), media_type="text/plain")
