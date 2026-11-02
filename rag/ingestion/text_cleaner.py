import re

from langchain_core.documents import Document


def clean_documents(documents: list[Document]) -> list[Document]:

    cleaned_documents = []

    for doc in documents:

        text = doc.page_content

        # Normalize special spaces
        text = text.replace("\xa0", " ")

        # Normalize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove excessive spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        text = text.strip()

        if not text:
            continue

        cleaned_documents.append(
            Document(page_content=text, metadata=dict(doc.metadata))
        )

    return cleaned_documents
