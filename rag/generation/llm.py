from langchain_google_genai import ChatGoogleGenerativeAI

from rag.config import GOOGLE_API_KEY, GEMINI_CHAT_MODEL


def get_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_CHAT_MODEL,
        google_api_key=GOOGLE_API_KEY,
        timeout=60,
        max_retries=1,
    )
