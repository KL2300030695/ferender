"""
Wellness Companion - Light & Airy UI (CustomTkinter)

Features:
- (New) Speech-to-Text (STT) for user input
- (New) Text-to-Speech (TTS) for bot responses
- Pastel/light theme UI (Option A)
- Rounded video pane with soft shadow
- Pastel chat bubbles (bot/user)
- Mood-adaptive accent tint (background/bubble highlight)
- Non-blocking threads for video capture and LLM calls
- Clear "thinking" indicator and disabled send while AI responds

Make sure:
- emotion_model.h5 is in working directory
- Ollama local server is available at OLLAMA_URL
- You have installed: pip install pyttsx3 speechrecognition PyAudio
"""

import os
import time
import threading
import json
import requests
import cv2
import numpy as np
import tensorflow as tf
import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import font as tkfont

# --- New Imports for Speech ---
try:
    import pyttsx3
    import speech_recognition as sr
except ImportError:
    print("Error: 'pyttsx3' or 'speechrecognition' libraries not found.")
    print("Please install them with: pip install pyttsx3 speechrecognition PyAudio")
    exit()
# -----------------------------

# ---------- CONFIG ----------
MODEL_PATH = "emotion_model.h5"
HAAR_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
IMG_WIDTH, IMG_HEIGHT = 48, 48

OLLAMA_URL = "http://localhost:11434/api/chat"
LLAMA_MODEL_NAME = "gemma:2b"  # your model

# ---------- COLOR THEME (Option A: Light & Airy) ----------
BG_MAIN = "#F7FAFC"  # main window background (soft white-blue)
CARD_BG = "#FFFFFF"  # cards and containers
ACCENT = "#66B2FF"  # primary accent (sky blue)
MINT = "#A8E6CF"  # mint accent for positive mood
TEXT_PRIMARY = "#333333"  # dark text
TEXT_SECONDARY = "#6C757D"  # secondary text
BOT_BUBBLE = "#E3F2FD"  # light sky blue (bot)
USER_BUBBLE = "#EAF4F4"  # pale mint (user)
SHADOW = "#E6EEF6"

# ---------- App ----------
ctk.set_appearance_mode("light")  # keep UI light
ctk.set_default_color_theme("blue")

class WellnessCompanion(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Your Wellness Companion 🌼")
        self.geometry("1200x720")
        self.configure(fg_color=BG_MAIN)

        # App state
        self.cap = cv2.VideoCapture(0)
        self.thread_stop_event = threading.Event()
        self.last_emotion_time = time.time()
        self.emotion_cooldown = 10
        self.conversation_history = []
        
        # --- New States for Speech ---
        self.is_ai_thinking = False
        self.is_speaking = False
        self.is_listening = False
        # -----------------------------

        # load models
        self.load_models()

        # --- Initialize Speech Engines ---
        try:
            self.tts_engine = pyttsx3.init()
            # Optional: Set a more natural-sounding voice
            voices = self.tts_engine.getProperty('voices')
            if len(voices) > 1:
                self.tts_engine.setProperty('voice', voices[1].id) # Index 1 is often female
            self.tts_engine.setProperty('rate', 160) # Adjust speed
        except Exception as e:
            print(f"Warning: Could not initialize TTS engine: {e}")
            self.tts_engine = None

        self.recognizer = sr.Recognizer()
        # --------------------------------

        # fonts (CustomTkinter widgets accept tuples: (family, size, weight))
        try:
            self.heading_font = ("Poppins", 20, "bold")
            self.body_font = ("Poppins", 13)
        except Exception:
            # Fallback if Poppins causes an issue (unlikely for a tuple)
            self.heading_font = ("Segoe UI", 20, "bold")
            self.body_font = ("Segoe UI", 13)

        # grid layout: left = video, right = chat
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # --- Left: Camera panel ---
        self.left_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        self.left_card.grid(row=0, column=0, padx=(28, 14), pady=28, sticky="nsew")
        self.left_card.grid_rowconfigure(0, weight=1) # Was 0, changed to 1
        self.left_card.grid_columnconfigure(0, weight=1)

        # Title area
        header_frame = ctk.CTkFrame(self.left_card, fg_color=CARD_BG, corner_radius=12, height=60)
        header_frame.grid(row=0, column=0, sticky="new", padx=18, pady=(18, 6))
        header_frame.grid_columnconfigure(0, weight=1)
        
        lbl_header = ctk.CTkLabel(header_frame, text="Live Camera", text_color=TEXT_PRIMARY,
                                  font=self.heading_font, fg_color=CARD_BG)
        lbl_header.grid(row=0, column=0, sticky="w")

        # Camera display area
        cam_container = ctk.CTkFrame(self.left_card, fg_color=SHADOW, corner_radius=14)
        cam_container.grid(row=1, column=0, padx=18, pady=12, sticky="nsew") # This should be row 1
        cam_container.grid_rowconfigure(0, weight=1)
        cam_container.grid_columnconfigure(0, weight=1)

        self.video_frame = ctk.CTkFrame(cam_container, fg_color=CARD_BG, corner_radius=12)
        self.video_frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        # video label (PIL image)
        self.video_label = ctk.CTkLabel(self.video_frame, text="", fg_color=CARD_BG)
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # emotion badge
        self.emotion_badge = ctk.CTkLabel(self.video_frame, text="Mood: Neutral", width=150,
                                          corner_radius=12, fg_color=USER_BUBBLE, text_color=TEXT_PRIMARY,
                                          anchor="w", padx=10)
        self.emotion_badge.place(relx=0.02, rely=0.86)  # bottom-left of camera

        # --- Right: Chat panel ---
        self.right_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=16)
        self.right_card.grid(row=0, column=1, padx=(14, 28), pady=28, sticky="nsew")
        self.right_card.grid_rowconfigure(1, weight=1)
        self.right_card.grid_columnconfigure(0, weight=1)

        # Header
        title = ctk.CTkLabel(self.right_card, text="Your Wellness Companion", font=self.heading_font,
                             text_color=TEXT_PRIMARY, fg_color=CARD_BG, anchor="w")
        title.grid(row=0, column=0, padx=18, pady=(18, 6), sticky="ew")

        # Chat history area (scrollable)
        self.chat_box = ctk.CTkTextbox(self.right_card, wrap="word", state="disabled",
                                       width=420, corner_radius=12, fg_color="#FAFCFD",
                                       font=("Segoe UI", 12), padx=12, pady=12)
        self.chat_box.grid(row=1, column=0, padx=18, pady=8, sticky="nsew")

        # style tags
        self.chat_box.tag_config("bot_sender", foreground=ACCENT)
        self.chat_box.tag_config("bot_msg", foreground=TEXT_PRIMARY, lmargin1=8, lmargin2=8)
        self.chat_box.tag_config("user_sender", foreground=TEXT_SECONDARY)
        self.chat_box.tag_config("user_msg", foreground=TEXT_PRIMARY, lmargin1=8, lmargin2=8, justify="right")

        # Input area
        input_area = ctk.CTkFrame(self.right_card, fg_color=CARD_BG, corner_radius=12)
        input_area.grid(row=2, column=0, padx=18, pady=(6, 18), sticky="ew")
        input_area.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(input_area, placeholder_text="How are you feeling? Share a little...", height=44)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(8, 10), pady=10)
        self.entry.bind("<Return>", self._on_send)

        # --- New Record Button ---
        self.record_button = ctk.CTkButton(input_area, text="🎤", width=44, height=44,
                                           corner_radius=12, command=self._on_record,
                                           font=("Segoe UI", 16)) # Mic emoji
        self.record_button.grid(row=0, column=1, padx=(0, 10), pady=10)
        # -------------------------

        self.send_button = ctk.CTkButton(input_area, text="Send", width=80, corner_radius=12, command=self._on_send, height=44)
        self.send_button.grid(row=0, column=2, padx=(0, 8), pady=10) # Moved to column 2

        # small status label
        self.status_label = ctk.CTkLabel(self.right_card, text="", text_color=TEXT_SECONDARY, fg_color=CARD_BG, anchor="w")
        self.status_label.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 18))

        # Start conversation + video thread
        self.start_conversation()
        self.video_thread = threading.Thread(target=self._video_loop, daemon=True)
        self.video_thread.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------
    # Model loading & helper
    # -------------------------
    def load_models(self):
        try:
            self.model = tf.keras.models.load_model(MODEL_PATH)
        except Exception as e:
            self.show_fatal(f"Unable to load emotion model: {e}")

        try:
            self.face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
            if self.face_cascade.empty():
                raise IOError("Haar cascade failed to load")
        except Exception as e:
            self.show_fatal(f"Unable to load face cascade: {e}")

    # -------------------------
    # Video loop & emotion detection
    # -------------------------
    def _video_loop(self):
        while not self.thread_stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.02)
                continue

            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

            detected_emotion = "neutral"
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                face_gray = gray[y:y+h, x:x+w]
                try:
                    face_resized = cv2.resize(face_gray, (IMG_WIDTH, IMG_HEIGHT))
                    roi = np.expand_dims(np.expand_dims(face_resized, -1), 0) / 255.0
                    pred = self.model.predict(roi, verbose=0)[0]
                    detected_emotion = EMOTION_LABELS[int(np.argmax(pred))]
                except Exception:
                    detected_emotion = "neutral"

                # draw rectangle & label
                color = (100, 180, 160)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, detected_emotion.capitalize(), (x, y - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # update UI badge
            self.after(0, self._update_mood_ui, detected_emotion)

            # trigger an empathetic interjection
            # (Check all states before interjecting)
            can_interject = not (self.is_ai_thinking or self.is_speaking or self.is_listening)
            if can_interject and (time.time() - self.last_emotion_time) > self.emotion_cooldown \
               and detected_emotion not in ("neutral", "happy"):
                self.last_emotion_time = time.time()
                threading.Thread(target=self._ask_about_emotion, args=(detected_emotion,), daemon=True).start()

            # convert frame to image for Tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            
            display_w = int(self.video_frame.winfo_width() * 0.96) or 540
            display_h = int(self.video_frame.winfo_height() * 0.96) or 360
            
            img = img.resize((display_w, display_h), Image.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)

            self.after(0, lambda i=img_tk: self._set_video_image(i))
            time.sleep(0.03)

    def _set_video_image(self, img_tk):
        self.video_label.configure(image=img_tk)
        self.video_label.image = img_tk

    def _update_mood_ui(self, emotion):
        display = emotion.capitalize()
        self.emotion_badge.configure(text=f"Mood: {display}")
        if emotion == "happy":
            tone = MINT
        elif emotion == "sad":
            tone = "#FFE9B6" 
        elif emotion in ("angry", "disgust", "fear"):
            tone = "#FFD3D3"
        else:
            tone = USER_BUBBLE
        self.emotion_badge.configure(fg_color=tone)

    # -------------------------
    # Chat / LLM integration
    # -------------------------
    def start_conversation(self):
        system_prompt = {
            "role": "system",
            "content": "You are a gentle, empathetic AI wellness companion. Be supportive and concise. Do not provide medical advice."
        }
        opening = "Hello 🌿 I'm your AI Wellness Companion. How are you feeling today?"
        self.conversation_history = [system_prompt, {"role": "assistant", "content": opening}]
        self._add_bot_message(opening)
        
        # --- Speak opening message ---
        self._speak_message_in_thread(opening)
        # ----------------------------

    def _on_send(self, event=None):
        if self.is_ai_thinking or self.is_listening or self.is_speaking:
            return
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._add_user_message(text)
        self.conversation_history.append({"role": "user", "content": text})
        threading.Thread(target=self._get_llm_response, daemon=True).start()

    def _ask_about_emotion(self, emotion):
        if self.is_ai_thinking or self.is_listening or self.is_speaking:
            return
        prompt = f"[User appears {emotion}. Ask gently how they're feeling and offer support.]"
        self.conversation_history.append({"role": "user", "content": prompt})
        threading.Thread(target=self._get_llm_response, args=(True,), daemon=True).start()

    def _get_llm_response(self, emotion_context=False):
        self.is_ai_thinking = True
        self.after(0, self._update_ui_states) # Update UI
        
        thinking_index = self._add_bot_message("💭 Thinking...", thinking=True)

        try:
            payload = {
                "model": LLAMA_MODEL_NAME,
                "messages": self.conversation_history,
                "stream": False
            }
            resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            ai_text = data.get("message", {}).get("content") or "I'm here — tell me more."
            
            self.after(0, self._update_bot_message, thinking_index, ai_text)
            self.conversation_history.append({"role": "assistant", "content": ai_text})
            
            # --- Speak the response ---
            self._speak_message_in_thread(ai_text)
            # --------------------------

        except requests.exceptions.Timeout:
            err_msg = "The model timed out. Please try again."
            self.after(0, self._update_bot_message, thinking_index, err_msg)
        except requests.exceptions.RequestException as e:
            err_msg = "Connection error with local LLM."
            self.after(0, self._update_bot_message, thinking_index, err_msg)
        except Exception as e:
            err_msg = "An unexpected error occurred."
            self.after(0, self._update_bot_message, thinking_index, err_msg)
        finally:
            self.is_ai_thinking = False
            # Don't update UI states here, let the speak thread handle it
            # if it's speaking. If not, the speak thread won't run.
            if not self.is_speaking:
                 self.after(0, self._update_ui_states)


    # -------------------------
    # --- New Speech Methods ---
    # -------------------------
    
    def _speak_message_in_thread(self, text):
        """Starts the TTS function in a new thread."""
        if not self.tts_engine:
            self.is_ai_thinking = False
            self.after(0, self._update_ui_states)
            return
            
        threading.Thread(target=self._speak_message, args=(text,), daemon=True).start()

    def _speak_message(self, text):
        """(Worker) Runs TTS engine. This is blocking, so run in a thread."""
        if self.thread_stop_event.is_set():
            return
            
        self.is_speaking = True
        self.after(0, self._update_ui_states)
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            self.is_speaking = False
            self.is_ai_thinking = False # Also clear thinking flag
            self.after(0, self._update_ui_states)

    def _on_record(self):
        """(Trigger) Starts the listening thread."""
        if self.is_ai_thinking or self.is_listening or self.is_speaking:
            return
        threading.Thread(target=self._listen_and_transcribe, daemon=True).start()

    def _listen_and_transcribe(self):
        """(Worker) Listens for voice and transcribes it."""
        self.is_listening = True
        self.after(0, self._update_ui_states)
        
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.after(0, self._set_status, "Listening... 🎤", accent=True)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            self.after(0, self._set_status, "Transcribing...", accent=True)
            
            # Recognize speech using Google Web Speech API
            text = self.recognizer.recognize_google(audio).strip()
            
            # Update the entry box from the main thread
            self.after(0, lambda t=text: self.entry.insert(0, t))
            
        except sr.WaitTimeoutError:
            self.after(0, self._set_status, "Listening timed out.", accent=False)
        except sr.UnknownValueError:
            self.after(0, self._set_status, "Sorry, I didn't catch that.", accent=False)
        except sr.RequestError as e:
            self.after(0, self._set_status, f"Speech API error: {e}", accent=False)
        except Exception as e:
            self.after(0, self._set_status, f"Listening error: {e}", accent=False)
        finally:
            self.is_listening = False
            self.after(0, self._update_ui_states)


    # -------------------------
    # Chat UI helpers
    # -------------------------

    def _update_ui_states(self):
        """Central function to manage button states and status label."""
        
        if self.is_listening:
            # State: Listening
            send_state = "disabled"
            record_state = "disabled"
            self._set_status("Listening... 🎤", accent=True)
            self.record_button.configure(text="...")

        elif self.is_speaking:
            # State: Speaking
            send_state = "disabled"
            record_state = "disabled"
            self._set_status("Companion is speaking... 🔊", accent=True)
            self.record_button.configure(text="🎤")

        elif self.is_ai_thinking:
            # State: Thinking
            send_state = "disabled"
            record_state = "disabled"
            self._set_status("Companion is thinking... 💭", accent=True)
            self.record_button.configure(text="🎤")
            
        else:
            # State: Idle
            send_state = "normal"
            record_state = "normal"
            self._set_status("", accent=False) # Clear status
            self.record_button.configure(text="🎤")

        self.send_button.configure(state=send_state)
        self.record_button.configure(state=record_state)


    def _add_bot_message(self, text, thinking=False):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", "🤗 Companion:\n", ("bot_sender",))
        if thinking:
            self.chat_box.insert("end", f"{text}\n\n", ("bot_msg",))
        else:
            self.chat_box.insert("end", f"{text}\n\n", ("bot_msg",))
        self.chat_box.configure(state="disabled")
        self.chat_box.yview_moveto(1.0)
        return self.chat_box.index("end - 2 lines")

    def _update_bot_message(self, index_str, new_text):
        self.chat_box.configure(state="normal")
        try:
            self.chat_box.delete(index_str + " linestart", "end-1c")
        except Exception:
            pass
        
        self.chat_box.insert("end", "🤗 Companion:\n", ("bot_sender",))
        self.chat_box.insert("end", f"{new_text}\n\n", ("bot_msg",))
        self.chat_box.configure(state="disabled")
        self.chat_box.yview_moveto(1.0)

    def _add_user_message(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", "You:\n", ("user_sender",))
        self.chat_box.insert("end", f"{text}\n\n", ("user_msg",))
        self.chat_box.configure(state="disabled")
        self.chat_box.yview_moveto(1.0)

    def _set_status(self, txt, accent=False):
        if accent:
            self.status_label.configure(text=txt, text_color=ACCENT)
        else:
            self.status_label.configure(text=txt, text_color=TEXT_SECONDARY)

    # -------------------------
    # Shutdown & errors
    # -------------------------
    def _on_close(self):
        self.thread_stop_event.set()
        
        # Stop TTS
        if self.tts_engine and self.is_speaking:
            try:
                self.tts_engine.stop()
            except Exception as e:
                print(f"Error stopping TTS: {e}")

        try:
            if self.video_thread.is_alive():
                self.video_thread.join(timeout=1.0)
        except Exception:
            pass
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

    def show_fatal(self, message):
        print("FATAL:", message)
        from tkinter import messagebox
        try:
            messagebox.showerror("Fatal Error", message)
        except Exception:
            pass
        self.destroy()
        raise SystemExit(message)


if __name__ == "__main__":
    
    # Check for microphone
    try:
        sr.Microphone()
    except Exception as e:
        print(f"FATAL: No microphone found or PyAudio not installed correctly. {e}")
        from tkinter import messagebox
        messagebox.showerror("Fatal Error", "No microphone found or PyAudio is missing. Please check your hardware and installation.")
        exit()

    app = WellnessCompanion()

    app.chat_box.tag_config("bot_sender", foreground=ACCENT)
    app.chat_box.tag_config("bot_msg", foreground=TEXT_PRIMARY, spacing3=8)
    app.chat_box.tag_config("user_sender", foreground=TEXT_SECONDARY)
    app.chat_box.tag_config("user_msg", foreground=TEXT_PRIMARY, spacing3=8)

    app.mainloop()