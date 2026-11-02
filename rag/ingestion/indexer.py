from pathlib import Path
from typing import Iterable

from rag.ingestion.pdf_loader import load_pdf_pages
from rag.ingestion.text_cleaner import clean_documents
from rag.ingestion.chunker import split_documents

from rag.vectorstore.chroma_store import get_vectorstore, delete_document_chunks


def index_pdf(
    pdf_path: str | Path, machine_id: str, document_id: str, revision: str
) -> dict:
    """
    Extract, clean, chunk, embed and index one PDF.

    Designed to be called from Django after saving the uploaded PDF.
    """

    pdf_path = Path(pdf_path)

    # 1. Validate input
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    if not machine_id.strip():
        raise ValueError("Machine ID is required.")

    if not document_id.strip():
        raise ValueError("Document ID is required.")

    if not revision.strip():
        raise ValueError("Revision is required.")

    # 2. Extract pages
    pages = load_pdf_pages(
        pdf_path=str(pdf_path),
        machine_id=machine_id,
        document_id=document_id,
        revision=revision,
    )

    if not pages:
        raise ValueError("No pages were extracted from the PDF.")

    # 3. Clean text
    cleaned_pages = clean_documents(pages)

    # 4. Split into chunks
    chunks = split_documents(cleaned_pages)

    if not chunks:
        raise ValueError("No text chunks were generated.")

    # 5. Generate deterministic chunk IDs
    chunk_ids = []

    for index, chunk in enumerate(chunks):

        metadata = chunk.metadata

        chunk_id = (
            f"{document_id}"
            f"-rev-{revision}"
            f"-page-{metadata['page_number']}"
            f"-chunk-{index}"
        )

        chunk_ids.append(chunk_id)

    # 6. Replace existing document chunks
    # This prevents duplicate chunks when the same document is indexed again.
    delete_document_chunks(document_id)

    # 7. Store chunks and generate embeddings
    vectorstore = get_vectorstore()

    vectorstore.add_documents(documents=chunks, ids=chunk_ids)

    return {
        "success": True,
        "machine_id": machine_id,
        "document_id": document_id,
        "revision": revision,
        "filename": pdf_path.name,
        "total_pages": len(pages),
        "total_chunks": len(chunks),
        "status": "indexed",
    }


def index_pdfs(manuals: Iterable[dict]) -> list[dict]:
    """
    Index multiple PDFs.

    Each item must contain:
    pdf_path, machine_id, document_id, revision.
    """

    results = []

    for manual in manuals:

        result = index_pdf(
            pdf_path=manual["pdf_path"],
            machine_id=manual["machine_id"],
            document_id=manual["document_id"],
            revision=manual["revision"],
        )

        results.append(result)

    return results
