from rag.config import RETRIEVAL_K
from rag.retrieval.filters import machine_filter
from rag.vectorstore.chroma_store import get_vectorstore


def retrieve_documents(question: str, machine_id: str, k: int = None):
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    vectorstore = get_vectorstore()

    results = vectorstore.similarity_search_with_relevance_scores(
        query=question, k=k or RETRIEVAL_K, filter=machine_filter(machine_id)
    )

    return results
