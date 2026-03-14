import cv2
import numpy as np
import tensorflow as tf
import base64
import requests
import json
import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Body, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

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

# --- Authentication & DB Configuration ---
SECRET_KEY = "super-secret-wellness-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "wellness_ai"

# Database Connection
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db["users"]
sessions_collection = db["sessions"]

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Load Models ---
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    print("Models loaded successfully.")
except Exception as e:
    print(f"Error loading models: {e}")
    model = None
    face_cascade = None


# --- Pydantic Models for DB & Auth ---
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.str_schema(pattern='^[a-fA-F0-9]{24}$')

class UserRegister(BaseModel):
    email: str
    password: str
    first_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    
class SessionData(BaseModel):
    resilience_score: int
    empathy_level: str
    messages_count: int
    duration_seconds: int
    emotion_log: List[str]

# --- Auth Dependency ---
async def get_current_user(token: str = Depends(lambda req: req.headers.get("Authorization", "").replace("Bearer ", ""))):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    if not token:
        # Allow guest mode: returns None if no token
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: return None
    except JWTError:
        return None
    
    user = await users_collection.find_one({"email": email})
    if user is None: return None
    user["id"] = str(user["_id"])
    return user

async def require_user(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return current_user

# --- Authentication Routes ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/auth/register", response_model=Token)
async def register(user: UserRegister):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = pwd_context.hash(user.password)
    new_user = {
        "email": user.email,
        "password_hash": hashed_password,
        "first_name": user.first_name,
        "created_at": datetime.now(timezone.utc)
    }
    await users_collection.insert_one(new_user)
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin):
    db_user = await users_collection.find_one({"email": user.email})
    if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(require_user)):
    return {"email": current_user["email"], "first_name": current_user["first_name"], "id": current_user["id"]}

# --- User Session History Routes ---
@app.post("/users/me/sessions")
async def save_session(session: SessionData, current_user: dict = Depends(require_user)):
    session_dict = session.model_dump()
    session_dict["user_id"] = current_user["id"]
    session_dict["created_at"] = datetime.now(timezone.utc)
    await sessions_collection.insert_one(session_dict)
    return {"status": "success"}

@app.get("/users/me/sessions")
async def get_sessions(current_user: dict = Depends(require_user)):
    sessions = []
    cursor = sessions_collection.find({"user_id": current_user["id"]}).sort("created_at", -1)
    async for s in cursor:
        s["id"] = str(s["_id"])
        del s["_id"]
        sessions.append(s)
    return sessions

# --- Original Core Routes ---
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
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    messages = [m.model_dump() for m in request.messages]
    
    # Personalize if user is logged in
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
