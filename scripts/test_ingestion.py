from pathlib import Path

from rag.ingestion.pdf_loader import load_pdf_pages
from rag.ingestion.text_cleaner import clean_documents
from rag.ingestion.chunker import split_documents

ROOT = Path(__file__).resolve().parents[1]

pdf_path = ROOT / "data" / "manuals" / "HP200_Operations_Rev1_0.pdf"


# 1. Load PDF
documents = load_pdf_pages(
    pdf_path=pdf_path, machine_id="M-HP200", document_id="HP-OPS-01", revision="1.0"
)

print("Total pages extracted:", len(documents))


# 2. Clean text
cleaned_documents = clean_documents(documents)

print("Cleaned pages:", len(cleaned_documents))


# 3. Split documents
chunks = split_documents(cleaned_documents)

print("Total chunks:", len(chunks))


# 4. Inspect first chunk
if chunks:

    print("\nFIRST CHUNK")
    print("======================")

    print(chunks[0].page_content)

    print("\nMETADATA")
    print(chunks[0].metadata)
