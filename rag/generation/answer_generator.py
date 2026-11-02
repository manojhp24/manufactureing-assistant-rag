from rag.config import MIN_RELEVANCE_SCORE
from rag.retrieval.retriever import retrieve_documents
from rag.generation.llm import get_llm
from rag.generation.prompts import get_rag_prompt
from rag.generation.response_parser import parse_response

from rag.evaluation.evidence_evaluator import (
    evaluate_evidence,
    evaluate_semantic_evidence,
)

INSUFFICIENT_MESSAGE = (
    "Insufficient information in the available manuals " "to answer this question."
)


def format_context(results):

    context_parts = []

    for document, score in results:

        metadata = document.metadata

        context_parts.append(f"""
Document ID: {metadata.get('document_id')}
Revision: {metadata.get('revision')}
Machine ID: {metadata.get('machine_id')}
PDF Page: {metadata.get('page_number')}

Content:
{document.page_content}
""")

    return "\n\n".join(context_parts)


def generate_answer(question: str, machine_id: str):

    print("[DEBUG 1] Starting retrieval", flush=True)

    results = retrieve_documents(question=question, machine_id=machine_id)

    print(f"[DEBUG 2] Retrieved {len(results)} chunks", flush=True)

    relevant_results = [
        (document, score) for document, score in results if score >= MIN_RELEVANCE_SCORE
    ]

    if not relevant_results:

        return {
            "answer": INSUFFICIENT_MESSAGE,
            "status": "insufficient",
            "citations": [],
            "sources": [],
        }

    print("[DEBUG 3] Preparing context", flush=True)

    context = format_context(relevant_results)

    prompt = get_rag_prompt()

    print("[DEBUG 4] Initializing Gemini", flush=True)

    llm = get_llm()
    chain = prompt | llm

    print("[DEBUG 5] Sending request to Gemini", flush=True)

    response = chain.invoke(
        {"machine_id": machine_id, "question": question, "context": context}
    )

    print("[DEBUG 6] Gemini response received", flush=True)

    result = parse_response(response)

    print("[DEBUG 7] JSON validation successful", flush=True)

    # Validate citation metadata against retrieved evidence
    available_sources = {
        (
            doc.metadata.get("document_id"),
            doc.metadata.get("revision"),
            doc.metadata.get("page_number"),
        )
        for doc, score in relevant_results
    }

    citations = result["citations"]

    for citation in citations:

        citation_key = (
            citation["document_id"],
            citation["revision"],
            citation["page_number"],
        )

        if citation_key not in available_sources:
            raise ValueError(f"Invalid citation: {citation_key}")

    # Insufficient answers must not contain citations
    if result["status"] == "insufficient":
        citations = []

    # Return only sources referenced by citations
    citation_keys = {
        (citation["document_id"], citation["revision"], citation["page_number"])
        for citation in citations
    }

    sources = []

    for document, score in relevant_results:

        metadata = document.metadata

        source_key = (
            metadata.get("document_id"),
            metadata.get("revision"),
            metadata.get("page_number"),
        )

        if source_key in citation_keys:

            sources.append(
                {
                    "document_id": metadata.get("document_id"),
                    "revision": metadata.get("revision"),
                    "page_number": metadata.get("page_number"),
                    "source": metadata.get("source"),
                }
            )

            citation_keys.remove(source_key)

        # Step 1: Validate citation traceability
    evaluation = evaluate_evidence(
        response=result,
        retrieved_documents=[document for document, score in relevant_results],
    )

    if not evaluation["is_valid"]:
        return {
            "answer": INSUFFICIENT_MESSAGE,
            "status": "insufficient",
            "citations": [],
            "sources": [],
            "evaluation": evaluation,
        }

    # Step 2: Verify semantic evidence
    semantic_evaluation = evaluate_semantic_evidence(
        answer=result["answer"],
        retrieved_documents=[document for document, score in relevant_results],
    )

    if not semantic_evaluation["is_supported"]:
        return {
            "answer": INSUFFICIENT_MESSAGE,
            "status": "insufficient",
            "citations": [],
            "sources": [],
            "evaluation": {"is_valid": True, "semantic": semantic_evaluation},
        }

    return {
        "answer": result["answer"],
        "status": result["status"],
        "citations": citations,
        "sources": sources,
        "evaluation": {"is_valid": True, "semantic": semantic_evaluation},
    }
