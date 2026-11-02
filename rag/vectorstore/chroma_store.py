from langchain_chroma import Chroma

from rag.config import CHROMA_PERSIST_DIRECTORY, CHROMA_COLLECTION_NAME
from rag.embeddings.embedding_model import get_embedding_model


def get_vectorstore():

    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embedding_model(),
        persist_directory=CHROMA_PERSIST_DIRECTORY,
    )


def add_chunks(documents, ids=None):

    vectorstore = get_vectorstore()

    vectorstore.add_documents(documents=documents, ids=ids)

    return vectorstore._collection.count()


def delete_document_chunks(document_id: str):

    vectorstore = get_vectorstore()

    vectorstore.delete(where={"document_id": document_id})


def get_chunk_count():

    vectorstore = get_vectorstore()

    return vectorstore._collection.count()
