import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OpenScout – Personal Open Source Event Notifier"
    DEMO_MODE: bool = True
    DATABASE_URL: str = "sqlite:///./data/openscout.db"
    
    # Open-Weight AI Model config
    OLLAMA_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "gemma2:2b"
    NOTIFICATION_THRESHOLD: float = 0.80
    
    # Notifications
    NOTIFICATION_CHANNEL: str = "log"
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    NOTIFY_EMAIL_TO: str = "friend@example.com"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
