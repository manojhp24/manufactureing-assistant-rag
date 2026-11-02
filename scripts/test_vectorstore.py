from pathlib import Path

from rag.ingestion.pdf_loader import load_pdf_pages
from rag.ingestion.text_cleaner import clean_documents
from rag.ingestion.chunker import split_documents

from rag.vectorstore.chroma_store import add_chunks, get_chunk_count

ROOT = Path(__file__).resolve().parents[1]

pdf_path = ROOT / "data" / "manuals" / "HP200_Operations_Rev1_0.pdf"


# 1. Load PDF
documents = load_pdf_pages(
    pdf_path=str(pdf_path),
    machine_id="M-HP200",
    document_id="HP-OPS-01",
    revision="1.0",
)


# 2. Clean documents
cleaned_documents = clean_documents(documents)


# 3. Split documents
chunks = split_documents(cleaned_documents)


# 4. Store chunks
count = add_chunks(chunks)


print("Chunks stored successfully")

print("Total chunks in ChromaDB:", count)
