import cv2
import numpy as np
import tensorflow as tf
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import pyttsx3
import time
import json

# --- Constants ---
MODEL_PATH = 'emotion_model.h5'
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
IMG_WIDTH, IMG_HEIGHT = 48, 48

# --- Chatbot Responses ---
EMOTION_RESPONSES = {
    "happy": ["You look happy today! 😄", "Keep smiling! 🌟"],
    "sad": ["I'm here for you. 💖", "It's okay to feel sad sometimes."],
    "angry": ["Take a deep breath... 😌", "I understand you might be frustrated."],
    "surprise": ["Wow! You look surprised! 😲", "Something unexpected happened?"],
    "neutral": ["You seem calm today 😊", "All good?"],
    "fear": ["Don't worry, you're safe.", "Take a deep breath and relax."],
    "disgust": ["Hmm, something seems off?", "Take a moment to relax."]
}

# --- Voice Engine ---
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def speak(text):
    engine.say(text)
    engine.runAndWait()

# --- Conversation log ---
LOG_FILE = "chat_log.json"

def save_log(user_msg, bot_reply, emotion):
    entry = {"emotion": emotion, "user": user_msg, "bot": bot_reply, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(LOG_FILE, "a") as f:
        json.dump(entry, f)
        f.write("\n")

# --- Main App ---
class FERVoiceChatbot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FER Voice Chatbot")
        self.geometry("1000x650")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- Video Frame ---
        self.video_frame = ctk.CTkFrame(self, corner_radius=15)
        self.video_frame.pack(side="left", padx=20, pady=20, fill="both", expand=True)
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(expand=True)

        # --- Chat Frame ---
        self.chat_frame = ctk.CTkFrame(self, corner_radius=15)
        self.chat_frame.pack(side="right", padx=20, pady=20, fill="both", expand=True)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_history = ctk.CTkTextbox(self.chat_frame, state="disabled", wrap="word", font=("Calibri", 16), border_spacing=10)
        self.chat_history.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkEntry(input_frame, placeholder_text="Type your message here...", height=40)
        self.chat_input.grid(row=0, column=0, sticky="ew")
        self.chat_input.bind("<Return>", self.send_message)

        self.send_button = ctk.CTkButton(input_frame, text="Send", width=80, height=40, command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=(10,0))

        # --- Load models ---
        self.cap = cv2.VideoCapture(0)
        self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        self.model = tf.keras.models.load_model(MODEL_PATH)

        # --- App State ---
        self.stop_event = threading.Event()
        self.last_emotion_time = time.time()
        self.cooldown = 8  # seconds between replies

        # --- Start threads ---
        self.video_thread = threading.Thread(target=self.video_loop)
        self.video_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def video_loop(self):
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret: continue

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50,50))

            detected_emotion = "neutral"
            if len(faces) > 0:
                x, y, w, h = faces[0]
                roi_gray = gray[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
                roi = np.expand_dims(np.expand_dims(roi_gray, -1), 0) / 255.0
                pred = self.model.predict(roi, verbose=0)[0]
                detected_emotion = EMOTION_LABELS[np.argmax(pred)]

                cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)
                cv2.putText(frame, detected_emotion.capitalize(), (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

            # Auto voice response
            if time.time() - self.last_emotion_time > self.cooldown:
                if detected_emotion in EMOTION_RESPONSES:
                    reply = np.random.choice(EMOTION_RESPONSES[detected_emotion])
                    threading.Thread(target=speak, args=(reply,)).start()
                    self.add_message("Bot", reply)
                    save_log("Detected emotion", reply, detected_emotion)
                self.last_emotion_time = time.time()

            # Update GUI
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            img_tk = ImageTk.PhotoImage(img)
            self.video_label.configure(image=img_tk)
            self.video_label.image = img_tk
            time.sleep(0.03)

    def add_message(self, sender, message):
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}: {message}\n\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.yview_moveto(1.0)

    def send_message(self, event=None):
        msg = self.chat_input.get().strip()
        if not msg: return
        self.chat_input.delete(0, "end")
        self.add_message("You", msg)

        # Simple reply based on keywords (offline)
        reply = "Tell me more..."  # Default
        for emotion, responses in EMOTION_RESPONSES.items():
            if emotion in msg.lower():
                reply = np.random.choice(responses)
                break

        self.add_message("Bot", reply)
        threading.Thread(target=speak, args=(reply,)).start()
        save_log(msg, reply, "user_message")

    def on_closing(self):
        self.stop_event.set()
        if self.cap.isOpened(): self.cap.release()
        self.destroy()

# --- Run the app ---
if __name__ == "__main__":
    app = FERVoiceChatbot()
    app.mainloop()
