from fastapi import APIRouter, HTTPException
import base64
import numpy as np
import cv2
from app.models.emotion import EmotionRequest
from app.services.ml import ml_models

router = APIRouter(tags=["emotion"])
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
IMG_WIDTH, IMG_HEIGHT = 48, 48

@router.post("/detect-emotion")
async def detect_emotion(request: EmotionRequest):
    if ml_models.model is None or ml_models.face_cascade is None:
        raise HTTPException(status_code=500, detail="Models not loaded")

    try:
        header, encoded = request.image.split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
             return {"emotion": "neutral", "confidence": 0.0}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = ml_models.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(48, 48))

        detected_emotion = "neutral"
        confidence = 0.0

        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            roi_gray = gray[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
            roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0) / 255.0
            
            preds = ml_models.model.predict(roi, verbose=0)[0]
            idx = int(np.argmax(preds))
            detected_emotion = EMOTION_LABELS[idx]
            confidence = float(preds[idx])

        return {"emotion": detected_emotion, "confidence": confidence}

    except Exception as e:
        print(f"Detection Error: {e}")
        return {"emotion": "neutral", "confidence": 0.0}
