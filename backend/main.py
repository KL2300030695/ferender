import cv2
import numpy as np
import tensorflow as tf
import base64
import requests
import json
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
MODEL_PATH = "../emotion_model.h5"
HAAR_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
IMG_WIDTH, IMG_HEIGHT = 48, 48

OLLAMA_URL = "http://localhost:11434/api/chat"
LLAMA_MODEL_NAME = "gemma:2b"

# --- Load Models ---
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    print("Models loaded successfully.")
except Exception as e:
    print(f"Error loading models: {e}")
    model = None
    face_cascade = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    current_emotion: str

class EmotionRequest(BaseModel):
    image: str # base64 encoded image

@app.post("/detect-emotion")
async def detect_emotion(request: EmotionRequest):
    if model is None or face_cascade is None:
        raise HTTPException(status_code=500, detail="Models not loaded")

    try:
        # Decode base64 image
        header, encoded = request.image.split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
             return {"emotion": "neutral", "confidence": 0.0}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(48, 48))

        detected_emotion = "neutral"
        confidence = 0.0

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            roi_gray = gray[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
            roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0) / 255.0
            
            preds = model.predict(roi, verbose=0)[0]
            idx = np.argmax(preds)
            detected_emotion = EMOTION_LABELS[idx]
            confidence = float(preds[idx])

        return {"emotion": detected_emotion, "confidence": confidence}

    except Exception as e:
        print(f"Detection Error: {e}")
        return {"emotion": "neutral", "confidence": 0.0}

@app.post("/chat")
async def chat(request: ChatRequest):
    messages = [m.model_dump() for m in request.messages]
    
    # System prompt enhancement
    system_content = (
        "You are a world-class AI Wellness Companion, similar to Gemini or ChatGPT but specialized in empathy and emotional intelligence. "
        "Your responses should be supportive, insightful, and concise. "
        "You have access to the user's real-time facial emotion. "
        f"The user currently appears to feel: {request.current_emotion}. "
        "Tailor your response to this emotion without being overly clinical. Use markdown for better readability."
    )
    
    if messages[0]["role"] == "system":
        messages[0]["content"] = system_content
    else:
        messages.insert(0, {"role": "system", "content": system_content})

    async def stream_generator():
        try:
            payload = {
                "model": LLAMA_MODEL_NAME,
                "messages": messages,
                "stream": True
            }
            with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=60) as resp:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
