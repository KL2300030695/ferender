import cv2
import numpy as np
import tensorflow as tf
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import time
import requests # This library sends requests to your local Llama server
import os
import json

# --- Constants ---
MODEL_PATH = 'emotion_model.h5'
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
IMG_WIDTH, IMG_HEIGHT = 48, 48

# --- OLLAMA LOCAL SERVER URL ---
# This is the default address Ollama runs on.
OLLAMA_URL = "http://localhost:11434/api/chat" 

# --- THIS IS THE ONLY CHANGE ---
# We are swapping the 8-billion parameter model for a faster 2-billion parameter model
LLAMA_MODEL_NAME = "gemma:2b" 

class EmotionChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window and Theme ---
        self.title("AI Wellness Companion (Llama 3 Offline)")
        self.geometry("1100x680")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- App State ---
        self.cap = cv2.VideoCapture(0)
        self.thread_stop_event = threading.Event()
        self.last_emotion_time = time.time()
        self.emotion_cooldown = 10
        self.conversation_history = [] # This will store the chat history for Llama
        
        # --- NEW: Thinking Flag ---
        # This flag prevents multiple AI requests from being sent at the same time.
        self.is_ai_thinking = False

        # --- Load AI/ML Models ---
        self.load_models()

        # --- UI Layout ---
        self.grid_columnconfigure(0, weight=3) # Video
        self.grid_columnconfigure(1, weight=2) # Chat
        self.grid_rowconfigure(0, weight=1)

        # --- Video Frame ---
        self.video_frame = ctk.CTkFrame(self, fg_color="#101010", corner_radius=15)
        self.video_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(padx=10, pady=10, expand=True)

        # --- Chat Frame ---
        self.chat_frame = ctk.CTkFrame(self, corner_radius=15)
        self.chat_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkLabel(self.chat_frame, text="How are you feeling?", font=ctk.CTkFont(size=20, weight="bold"))
        header.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.chat_history_textbox = ctk.CTkTextbox(self.chat_frame, state="disabled", wrap="word", font=("Calibri", 16), border_spacing=10)
        self.chat_history_textbox.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        input_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(input_frame, placeholder_text="Share your thoughts...", height=40)
        self.chat_input.grid(row=0, column=0, sticky="ew")
        self.chat_input.bind("<Return>", self.send_message)
        
        self.send_button = ctk.CTkButton(input_frame, text="Send", width=80, height=40, command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=(10, 0))

        # --- Start ---
        self.start_conversation()
        self.video_thread = threading.Thread(target=self.video_loop)
        self.video_thread.start()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_models(self):
        try:
            self.model = tf.keras.models.load_model(MODEL_PATH)
            self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
            if self.face_cascade.empty(): raise IOError("Haar cascade file not found or is empty.")
        except Exception as e:
            self.show_error_and_exit(f"Failed to load models. Error: {e}")

    def video_loop(self):
        while not self.thread_stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret: 
                time.sleep(0.01)
                continue
            
            frame = cv2.flip(frame, 1)
            
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 5, minSize=(50, 50))
            
            detected_emotion = "neutral"
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                roi_gray = gray_frame[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
                roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0) / 255.0
                prediction = self.model.predict(roi, verbose=0)[0]
                detected_emotion = EMOTION_LABELS[np.argmax(prediction)]
                
                label_text = f"{detected_emotion.capitalize()}"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (70, 180, 120), 2)
                cv2.putText(frame, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (70, 180, 120), 2)

            # --- Check if AI is free AND if an emotion is detected ---
            if not self.is_ai_thinking and (time.time() - self.last_emotion_time) > self.emotion_cooldown and detected_emotion not in ["neutral", "happy"]:
                self.handle_emotion_interjection(detected_emotion)
                self.last_emotion_time = time.time()

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.after(0, self.update_video_label, img_tk)

    def update_video_label(self, img_tk):
        self.video_label.configure(image=img_tk)

    def send_message(self, event=None):
        # --- Check if AI is busy ---
        if self.is_ai_thinking:
            return
            
        user_message = self.chat_input.get()
        if not user_message.strip(): return
        
        self.add_message("You", user_message)
        self.chat_input.delete(0, "end")
        self.send_button.configure(state="disabled")
        
        # Add user message to Llama's history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Run Llama in a separate thread to avoid freezing the UI
        threading.Thread(target=self.get_llm_response).start()

    def get_llm_response(self, emotion_context=None):
        # --- SET FLAG: AI is now busy ---
        self.is_ai_thinking = True
        self.add_message("Companion", "...", is_thinking=True)
        
        try:
            # Add emotion context if it was just detected
            if emotion_context:
                emotion_prompt = f"[User's facial expression suggests they are feeling: {emotion_context}. Gently ask about it.]"
                self.conversation_history.append({"role": "user", "content": emotion_prompt})

            # Prepare the data payload for the Ollama API
            payload = {
                "model": LLAMA_MODEL_NAME,
                "messages": self.conversation_history,
                "stream": False # We want the full response at once
            }
            
            # Make the request to the local server
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()

            # Parse the response from Ollama
            data = response.json()
            ai_message = data.get('message', {}).get('content', 'Sorry, I had trouble thinking of a response.')
            
            self.update_last_message("Companion", ai_message)
            
            # Add Llama's response to the history
            self.conversation_history.append({"role": "assistant", "content": ai_message})
            if emotion_context:
                # Remove the temporary emotion prompt from history
                self.conversation_history.pop(-2) 

        except requests.exceptions.Timeout:
            self.update_last_message("Companion", "The Llama model is taking a very long time to respond (timeout). This is expected on a CPU.")
        except requests.exceptions.RequestException as e:
            print(f"--- Ollama Network Error --- \n{type(e).__name__}: {e}\n---------------------")
            self.update_last_message("Companion", "I can't connect to the Ollama server. Did you run 'ollama run llama3:8b' in your terminal?")
        finally:
            # --- SET FLAG: AI is now free ---
            self.is_ai_thinking = False
            self.send_button.configure(state="normal")

    def handle_emotion_interjection(self, emotion):
        """This function is called when a new emotion is detected"""
        
        # --- Check if AI is busy ---
        if self.is_ai_thinking:
            return

        self.send_button.configure(state="disabled")
        # Run the Llama response in a thread
        threading.Thread(target=self.get_llm_response, args=(emotion,)).start()

    def add_message(self, sender, message, is_thinking=False):
        self.after(0, self._add_message_thread_safe, sender, message)

    def _add_message_thread_safe(self, sender, message):
        self.chat_history_textbox.configure(state="normal")
        tag = "user" if sender == "You" else "companion"
        self.chat_history_textbox.insert("end", f"{sender}:\n", (tag + "_sender",))
        self.chat_history_textbox.insert("end", f"{message}\n\n", (tag + "_message",))
        self.chat_history_textbox.configure(state="disabled")
        self.chat_history_textbox.yview_moveto(1.0)
        
    def update_last_message(self, sender, message):
        self.after(0, self._update_last_message_thread_safe, sender, message)

    def _update_last_message_thread_safe(self, sender, message):
        self.chat_history_textbox.configure(state="normal")
        self.chat_history_textbox.delete("end-2l", "end-1l") 
        self.chat_history_textbox.insert("end-1l", f"{message}\n")
        self.chat_history_textbox.configure(state="disabled")
        self.chat_history_textbox.yview_moveto(1.0)

    def start_conversation(self):
        # Set the initial "system prompt" for the Llama model
        system_prompt = {
            "role": "system",
            "content": "You are an AI Wellness Companion. Your role is empathetic, supportive, and non-judgmental. You must not give medical advice. Keep your responses concise and caring."
        }
        self.conversation_history = [system_prompt]
        
        initial_prompt = "Hello! I'm your AI Wellness Companion. How are you feeling today?"
        self.add_message("Companion", initial_prompt)
        self.conversation_history.append({"role": "assistant", "content": initial_prompt})

    def on_closing(self):
        self.thread_stop_event.set()
        if hasattr(self, 'video_thread') and self.video_thread.is_alive(): 
            self.video_thread.join()
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

    def show_error_and_exit(self, message):
        print(f"FATAL ERROR: {message}")
        if hasattr(self, 'destroy'): self.destroy()
        exit()

if __name__ == "__main__":
    app = EmotionChatbotApp()
    app.chat_history_textbox.tag_config("user_sender", foreground="white")
    app.chat_history_textbox.tag_config("companion_sender", foreground="#77B4D3")
    app.chat_history_textbox.tag_config("user_message", lmargin1=10)
    app.chat_history_textbox.tag_config("companion_message", lmargin1=0)
    app.mainloop()


