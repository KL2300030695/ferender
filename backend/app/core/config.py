from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Wellness AI"
    MODEL_PATH: str = "../emotion_model.h5"
    HAAR_CASCADE_PATH: str = "haarcascade_frontalface_default.xml"
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    LLAMA_MODEL_NAME: str = "gemma:2b"
    SECRET_KEY: str = "super-secret-wellness-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "wellness_ai"

    class Config:
        env_file = ".env"

settings = Settings()
