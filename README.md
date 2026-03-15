# AI Wellness Companion

A cutting-edge, real-time AI Wellness Companion application designed to provide empathetic, personalized conversations. By leveraging local AI large language models and real-time facial emotion recognition, the companion reacts to a user's emotional state dynamically.

## Features

- **Real-Time Emotion Detection:** Analyzes the user's face via the webcam using OpenCV and a trained TensorFlow/Keras model to detect emotions (Happy, Sad, Angry, Fear, Disgust, Surprise, Neutral).
- **Empathetic AI Chat:** Uses `Ollama` running the `gemma:2b` model to generate context-aware, empathetic conversational responses based on the ongoing detected emotion.
- **Dynamic UI Metrics:** 
  - Tracks live session duration.
  - Automatically calculates an emotional "Resilience Score" based on bounce-back from negative feelings.
  - Evaluates an "Empathy Level" reflecting the depth of interaction.
- **Secure Authentication & Session History:** Features a complete JWT-based auth system powered by FastAPI and MongoDB. Users can sign up, log in, and auto-save their wellness sessions, complete with historical resilience scores and interaction counts, mapped securely to their account.
- **Modern Glassmorphic UI:** Built with React, Vite, and Framer Motion for smooth, accessible, and highly styled animations. Features independent Guest and Authenticated viewing modes.

---

## 🏗️ Architecture

- **Frontend:** React.js, Vite, React Router DOM, Framer Motion, Lucide-React.
- **Backend:** Python, FastAPI, Motor (Async MongoDB), standard cryptographic libraries (Passlib, PyJWT).
- **AI & ML:** TensorFlow/Keras (`emotion_model.h5`), OpenCV (Haar Cascades for face grouping).
- **Local LLM Engine:** Ollama (serving the local base model to maintain absolute data privacy).
- **Database:** MongoDB (Local, accessible at `mongodb://localhost:27017`).

---

## 🚀 Getting Started

Ensure you have [Python 3.9+](https://www.python.org/), [Node.js](https://nodejs.org/), [MongoDB Community Server](https://www.mongodb.com/try/download/community), and [Ollama](https://ollama.com/) installed on your machine.

### 1. Start the LLM Server
Start the Ollama server and ensure the `gemma:2b` model is downloaded and running on your device (default runs on `http://localhost:11434`).
```bash
ollama run gemma:2b
```

### 2. Start the Database
Ensure your MongoDB process is running in the background. The FastAPI server expects it open at `mongodb://localhost:27017` connecting to the `wellness_ai` database.

### 3. Backend Setup (FastAPI)
The backend requires the pre-trained Keras model in the root directory under the name `emotion_model.h5`.

```bash
cd backend
# Activate your virtual environment if preferred
python -m venv venv
venv\Scripts\activate # On Windows

# Install dependencies
pip install "fastapi[standard]" motor pymongo passlib[bcrypt] python-jose[cryptography] tensorflow opencv-python numpy requests

# Run the FastAPI server
python main.py
```
*The backend will be available at `http://localhost:8000`.*

### 4. Frontend Setup (React/Vite)
⚠️ **CRITICAL: You must execute these commands from inside the `frontend` directory.** If you see an error like `ENOENT: no such file or directory, open '...\package.json'`, it means you are in the wrong directory.

Open a new terminal window at the root of the project.

```bash
# Navigate into the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```
*The frontend will be available at `http://localhost:5173`. Navigate there to see the app!*

---

## 🔒 Privacy & Security

Mental health is highly private. This architecture is designed to protect users:
- **No Cloud Video:** The webcam stream is processed locally inside the Python backend using OpenCV. The video frames are **discarded** after emotion extraction.
- **No Cloud AI APIs:** All conversational responses are processed locally using your device's hardware via Ollama. No transcripts are sent out to OpenAI or other third-party services. 
- **Encrypted Credentials:** Passwords are mathematically hashed with `bcrypt`. Session tokens are secured using the industry-standard JSON Web Token (JWT) protocol.
