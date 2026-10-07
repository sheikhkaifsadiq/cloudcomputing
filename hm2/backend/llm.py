from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import get_settings
from backend.logger import get_logger

logger = get_logger(__name__)

def get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    logger.info(f"Initializing Gemini model: {settings.gemini_model}")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0.0
    )
