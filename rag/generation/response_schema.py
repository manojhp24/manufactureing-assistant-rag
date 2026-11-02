from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    page_number: int = Field(gt=0)
    text_passage: str = Field(default="", min_length=0)


class RAGResponse(BaseModel):
    answer: str = Field(min_length=1)

    status: Literal["answered", "insufficient", "conflict"]

    citations: list[Citation] = Field(default_factory=list)
