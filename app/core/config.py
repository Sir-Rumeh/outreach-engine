import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Outreach Engine Dashboard"
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

settings = Settings()

# Initialize Gemini Client if API key is configured
client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None