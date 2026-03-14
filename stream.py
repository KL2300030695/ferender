import cv2
import numpy as np
import tensorflow as tf
import requests
import os
import json
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase

# --- Constants ---
MODEL_PATH = 'emotion_model.h5'
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
IMG_WIDTH, IMG_HEIGHT = 48, 48

# --- OLLAMA LOCAL SERVER URL ---
OLLAMA_URL = "http://localhost:11434/api/chat"
LLAMA_MODEL_NAME = "gemma:2b"

# --- Load Models (Cache them so they only load once) ---
@st.cache_resource
def load_models():
    """Loads the emotion detection model and face cascade."""
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        if face_cascade.empty():
            st.error("Haar cascade file not found. Make sure it's in the correct path.")
            return None, None
        return model, face_cascade
    except Exception as e:
        st.error(f"Error loading models: {e}")
        return None, None

# --- Safe Session State Initialization ---
if 'model' not in st.session_state or st.session_state.get('model') is None:
    st.session_state.model, st.session_state.face_cascade = load_models()

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = [
        {
            "role": "system",
            "content": (
                "You are an AI Wellness Companion. Your role is empathetic, supportive, "
                "and non-judgmental. You must not give medical advice. Keep your responses concise and caring."
            )
        },
        {
            "role": "assistant",
            "content": "Hello! I'm your AI Wellness Companion. How are you feeling today?"
        }
    ]

if 'current_emotion' not in st.session_state:
    st.session_state.current_emotion = "neutral"

# --- Video Transformer Class ---
class EmotionTransformer(VideoTransformerBase):
    def __init__(self):
        # Thread-safe session initialization
        if "model" not in st.session_state or "face_cascade" not in st.session_state:
            model, face_cascade = load_models()
            st.session_state.model = model
            st.session_state.face_cascade = face_cascade

        self.model = st.session_state.model
        self.face_cascade = st.session_state.face_cascade

    def transform(self, frame):
        if self.model is None or self.face_cascade is None:
            return frame

        img = frame.to_ndarray(format="bgr24")
        gray_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 5, minSize=(50, 50))

        detected_emotion = "neutral"
        for (x, y, w, h) in faces:
            roi_gray = gray_frame[y:y+h, x:x+w]
            roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
            roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0) / 255.0

            prediction = self.model.predict(roi, verbose=0)[0]
            emotion_index = np.argmax(prediction)
            detected_emotion = EMOTION_LABELS[emotion_index]

            label_text = f"{detected_emotion.capitalize()}"
            cv2.rectangle(img, (x, y), (x+w, y+h), (70, 180, 120), 2)
            cv2.putText(img, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (70, 180, 120), 2)

        # Update the current detected emotion
        st.session_state.current_emotion = detected_emotion
        return img

# --- Helper Function for Llama ---
def get_llm_response(user_message, emotion_context):
    """Sends a message to the local Ollama server and gets a response."""
    full_user_prompt = f"{user_message} [User's emotion: {emotion_context}]"
    st.session_state.conversation_history.append({"role": "user", "content": full_user_prompt})

    try:
        payload = {
            "model": LLAMA_MODEL_NAME,
            "messages": st.session_state.conversation_history,
            "stream": False
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        ai_message = data.get('message', {}).get('content', 'Sorry, I had trouble thinking of a response.')

        st.session_state.conversation_history.append({"role": "assistant", "content": ai_message})
        return ai_message

    except requests.exceptions.RequestException as e:
        print(f"--- Ollama Network Error --- \n{type(e).__name__}: {e}\n---------------------")
        error_message = "I can't connect to the Ollama server. Is it running?"
        st.session_state.conversation_history.append({"role": "assistant", "content": error_message})
        return error_message

# --- Main App UI ---
st.set_page_config(layout="wide", page_title="AI Wellness Companion")
st.title("AI Wellness Companion")

col1, col2 = st.columns([6, 4])  # 60% for video, 40% for chat

# --- Column 1: Video Feed & Analysis ---
with col1:
    st.header("Live Video Feed")

    webrtc_streamer(
        key="emotion-detector",
        video_transformer_factory=EmotionTransformer,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    st.subheader("Live Emotion Analysis")
    st.metric("Current Detected Expression", st.session_state.current_emotion.capitalize())

# --- Column 2: Chat Interface ---
with col2:
    st.header("Wellness Chat")

    chat_container = st.container()

    with chat_container:
        for message in st.session_state.conversation_history:
            role = message["role"]
            if role == "system":
                continue
            with st.chat_message(role):
                st.write(message["content"])

    if prompt := st.chat_input("Share your thoughts..."):
        with chat_container:
            with st.chat_message("user"):
                st.write(prompt)

        emotion_context = st.session_state.current_emotion

        with st.spinner("Companion is thinking..."):
            ai_response = get_llm_response(prompt, emotion_context)
            with chat_container:
                with st.chat_message("assistant"):
                    st.write(ai_response)
