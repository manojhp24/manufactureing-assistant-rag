from langchain_google_genai import GoogleGenerativeAIEmbeddings

from rag.config import GOOGLE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


def get_embedding_model():

    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )

    return embeddings
