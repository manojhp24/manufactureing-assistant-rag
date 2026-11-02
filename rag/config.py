import os
from pathlib import Path

from dotenv import load_dotenv

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")


# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing in .env")


# Gemini Models
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")


# Embedding Configuration
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", 1024))


# Chunking Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))

CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))


# Retrieval Configuration
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", 6))

MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", 0.20))


# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY = str(
    (
        PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIRECTORY", "storage/chroma_db")
    ).resolve()
)

CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "manufacturing_manuals")
