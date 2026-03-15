import cv2
import tensorflow as tf
from app.core.config import settings

class MLModels:
    model = None
    face_cascade = None

ml_models = MLModels()

def load_models():
    try:
        ml_models.model = tf.keras.models.load_model(settings.MODEL_PATH)
        ml_models.face_cascade = cv2.CascadeClassifier(settings.HAAR_CASCADE_PATH)
        print("Models loaded successfully.")
    except Exception as e:
        print(f"Error loading models: {e}")
