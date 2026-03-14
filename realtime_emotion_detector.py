import cv2
import numpy as np
import tensorflow as tf
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import time
from collections import deque

# --- Constants ---
MODEL_PATH = 'emotion_model.h5'
HAAR_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
EMOTION_LABELS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
IMG_WIDTH, IMG_HEIGHT = 48, 48

class EmotionChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("AI Wellness Chatbot")
        self.geometry("1000x600")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")

        # --- App State ---
        self.cap = cv2.VideoCapture(0)
        self.thread_stop_event = threading.Event()
        self.last_emotion_time = time.time()
        self.emotion_cooldown = 7  # seconds

        # --- Load Models ---
        self.load_models()

        # --- UI Layout ---
        self.grid_columnconfigure(0, weight=2) # Video column
        self.grid_columnconfigure(1, weight=1) # Chat column
        self.grid_rowconfigure(0, weight=1)

        # --- Video Frame ---
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # --- Chat Frame ---
        self.chat_frame = ctk.CTkFrame(self)
        self.chat_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_history = ctk.CTkTextbox(self.chat_frame, state="disabled", wrap="word", font=("Arial", 14))
        self.chat_history.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.chat_input = ctk.CTkEntry(self.chat_frame, placeholder_text="Type your message...", font=("Arial", 14))
        self.chat_input.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.chat_input.bind("<Return>", self.send_message)

        # --- Start ---
        self.add_message("Chatbot: Hello! I'm an AI wellness assistant. How are you feeling today?")
        self.video_thread = threading.Thread(target=self.video_loop)
        self.video_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_models(self):
        """Loads the emotion detection model and face cascade."""
        try:
            self.model = tf.keras.models.load_model(MODEL_PATH)
        except (IOError, ImportError):
            self.show_error_and_exit(f"Could not load model '{MODEL_PATH}'. Please train it first.")
        
        self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
        if self.face_cascade.empty():
            self.show_error_and_exit("Could not load Haar Cascade face detector.")

    def video_loop(self):
        """Main loop to capture video, detect emotions, and update the UI."""
        while not self.thread_stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            frame = cv2.flip(frame, 1)
            
            # --- Emotion Detection Logic ---
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 5, minSize=(40, 40))
            
            for (x, y, w, h) in faces:
                roi_gray = gray_frame[y:y+h, x:x+w]
                roi_gray = cv2.resize(roi_gray, (IMG_WIDTH, IMG_HEIGHT))
                
                roi = np.expand_dims(roi_gray, axis=-1)
                roi = np.expand_dims(roi, axis=0) / 255.0

                prediction = self.model.predict(roi, verbose=0)[0]
                emotion_index = np.argmax(prediction)
                emotion_label = EMOTION_LABELS[emotion_index]
                
                # Update chatbot based on emotion with a cooldown
                if (time.time() - self.last_emotion_time) > self.emotion_cooldown:
                    chatbot_response = self.get_chatbot_response(emotion_label)
                    self.add_message(f"Chatbot: {chatbot_response}", from_ai=True)
                    self.last_emotion_time = time.time()
                
                # --- Drawing on frame ---
                label_text = f"{emotion_label}: {prediction[emotion_index]*100:.1f}%"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # --- Update UI with new frame ---
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            
            self.video_label.configure(image=img_tk)
            self.video_label.image = img_tk

    def send_message(self, event=None):
        """Handles sending a user's message to the chat."""
        user_message = self.chat_input.get()
        if user_message.strip() != "":
            self.add_message(f"You: {user_message}")
            self.chat_input.delete(0, "end")
            # Simple rule-based response for interactivity
            self.after(500, lambda: self.add_message("Chatbot: Thank you for sharing."))
            
    def add_message(self, message, from_ai=False):
        """Adds a message to the chat history box."""
        self.chat_history.configure(state="normal")
        if from_ai:
            self.chat_history.insert("end", message + "\n\n", "ai_message")
        else:
            self.chat_history.insert("end", message + "\n\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.yview("end") # Auto-scroll to the bottom

    def get_chatbot_response(self, emotion):
        """Provides a context-aware response based on the detected emotion."""
        responses = {
            'angry': "I'm noticing you might be feeling angry. It's okay to feel that way.",
            'fear': "You seem to be showing signs of fear. Remember to breathe, you are in a safe space here.",
            'happy': "It's wonderful to see a smile! Your expression suggests you're feeling happy right now.",
            'sad': "I'm sensing some sadness in your expression. I'm here to listen if you want to talk about it.",
            'surprise': "You look surprised! I hope it's for a good reason.",
            'neutral': "Your expression seems neutral. A great time for some calm reflection."
        }
        return responses.get(emotion, "I'm here to listen to whatever is on your mind.")

    def on_closing(self):
        """Handles the application closing event."""
        print("Closing application...")
        self.thread_stop_event.set()
        self.video_thread.join()
        self.cap.release()
        self.destroy()

    def show_error_and_exit(self, message):
        """Displays an error message in the terminal and exits."""
        print(f"FATAL ERROR: {message}")
        self.destroy()
        exit()


if __name__ == "__main__":
    app = EmotionChatbotApp()
    # Configure a tag for AI messages to have a different color (optional)
    app.chat_history.tag_config("ai_message", foreground="#00A0B0")
    app.mainloop()