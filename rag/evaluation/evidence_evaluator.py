from rag.generation.response_schema import RAGResponse


def evaluate_evidence(response: dict, retrieved_documents: list) -> dict:
    """
    Validate whether the response citations refer to
    retrieved documents and whether the response has
    sufficient evidence to support its answer.
    """

    if response["status"] == "insufficient":
        return {
            "is_valid": True,
            "reason": "The system correctly identified insufficient information.",
        }

    if not retrieved_documents:
        return {"is_valid": False, "reason": "No supporting documents were retrieved."}

    available_sources = {
        (
            doc.metadata.get("document_id"),
            doc.metadata.get("revision"),
            doc.metadata.get("page_number"),
        )
        for doc in retrieved_documents
    }

    citations = response.get("citations", [])

    if not citations:
        return {"is_valid": False, "reason": "The answer has no citations."}

    for citation in citations:
        citation_key = (
            citation["document_id"],
            citation["revision"],
            citation["page_number"],
        )

        if citation_key not in available_sources:
            return {
                "is_valid": False,
                "reason": f"Citation not found in retrieved evidence: {citation_key}",
            }

    return {
        "is_valid": True,
        "reason": "All citations match retrieved document metadata.",
    }


from rag.generation.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
import json

EVIDENCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a strict evidence verification system for manufacturing manuals.

Your task is to determine whether the generated answer is fully supported
by the supplied manual evidence.

Rules:
1. Do not use external knowledge.
2. Every factual claim must be supported by the evidence.
3. Numerical values and units must match exactly.
4. Reject unsupported technical instructions.
5. Reject claims that contradict the evidence.
6. If evidence is insufficient, mark the answer unsupported.

Return ONLY valid JSON:

{{
    "is_supported": true,
    "reason": "Explanation"
}}

or

{{
    "is_supported": false,
    "reason": "Explanation"
}}
""",
        ),
        (
            "human",
            """
Manual Evidence:
{context}

Generated Answer:
{answer}
""",
        ),
    ]
)


def evaluate_semantic_evidence(answer: str, retrieved_documents: list) -> dict:

    if not retrieved_documents:
        return {
            "is_supported": False,
            "reason": "No supporting documents were retrieved.",
        }

    context = "\n\n".join(document.page_content for document in retrieved_documents)

    llm = get_llm()

    response = (EVIDENCE_PROMPT | llm).invoke({"context": context, "answer": answer})

    content = response.content

    if isinstance(content, list):
        content = "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )

    content = content.strip()

    if content.startswith("```"):
        content = content.replace("```json", "", 1)
        content = content.replace("```", "").strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        return {
            "is_supported": False,
            "reason": "Evidence evaluator returned invalid JSON.",
        }

    if not isinstance(result.get("is_supported"), bool):
        return {
            "is_supported": False,
            "reason": "Invalid evidence evaluation response.",
        }

    return result
