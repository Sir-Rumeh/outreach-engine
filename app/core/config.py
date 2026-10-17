import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Outreach Engine Dashboard"
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

settings = Settings()

# Initialize Gemini Client if API key is configured
client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None