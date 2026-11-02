from rag.evaluation.evidence_evaluator import evaluate_semantic_evidence
from rag.retrieval.retriever import retrieve_documents


def test_evidence(question, answer, machine_id="M-HP200"):

    results = retrieve_documents(question=question, machine_id=machine_id)

    documents = [document for document, score in results]

    evaluation = evaluate_semantic_evidence(
        answer=answer, retrieved_documents=documents
    )

    print("\nQUESTION:", question)
    print("GENERATED ANSWER:", answer)
    print("EVALUATION:", evaluation)
    print("-" * 60)


if __name__ == "__main__":

    print("\nTEST 1: CORRECT ANSWER")

    test_evidence(
        question="What does error code E17 mean?",
        answer=(
            "E17 means low hydraulic pressure. "
            "It occurs when pressure stays below "
            "110 bar for more than 5 seconds during forming."
        ),
    )

    print("\nTEST 2: INCORRECT ANSWER")

    test_evidence(
        question="What does error code E17 mean?",
        answer="E17 means high hydraulic pressure above 200 bar.",
    )
