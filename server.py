from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Allow requests from your local machine

# --- Gemini Model Setup ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    # This will be set on the server, not in a local .env file
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

@app.route('/chat', methods=['POST'])
def chat_with_gemini():
    """Receives chat history and returns a new response from Gemini."""
    try:
        data = request.json
        if not data or 'prompt_parts' not in data:
            return jsonify({"error": "Invalid request. 'prompt_parts' is required."}), 400

        prompt_parts = data['prompt_parts']
        
        # Call the Gemini API
        response = model.generate_content(prompt_parts)
        
        if response and response.text:
            return jsonify({"response": response.text})
        else:
            return jsonify({"error": "Received an empty response from the API."}), 500

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": f"An internal server error occurred: {e}"}), 500

if __name__ == '__main__':
    # This is for local testing only. 
    # The hosting service will run the app in a production-ready way.
    app.run(port=5000, debug=True)
