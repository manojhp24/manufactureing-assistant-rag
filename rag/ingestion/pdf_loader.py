from pathlib import Path

import pymupdf
from langchain_core.documents import Document


def load_pdf_pages(
    pdf_path: str,
    machine_id: str,
    document_id: str,
    revision: str,
) -> list[Document]:

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    documents = []

    with pymupdf.open(path) as pdf:

        for page_index, page in enumerate(pdf):

            text = page.get_text("text")

            if not text.strip():
                continue

            metadata = {
                "machine_id": machine_id,
                "document_id": document_id,
                "revision": revision,
                "page_number": page_index + 1,
                "source": path.name,
            }

            document = Document(page_content=text, metadata=metadata)

            documents.append(document)

    return documents
