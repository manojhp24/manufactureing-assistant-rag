import argparse

from rag.retrieval.retriever import retrieve_documents


def run_test(question: str, machine_id: str):

    print("\nMachine ID:", machine_id)
    print("Question:", question)

    results = retrieve_documents(question=question, machine_id=machine_id)

    if not results:
        print("\nNo relevant documents found.")
        return

    print(f"\nRetrieved chunks: {len(results)}")

    for index, (document, score) in enumerate(results, start=1):

        metadata = document.metadata

        print("\n" + "=" * 60)
        print(f"RESULT {index}")
        print("=" * 60)

        print("Relevance Score:", round(score, 4))
        print("Machine ID:", metadata.get("machine_id"))
        print("Document ID:", metadata.get("document_id"))
        print("Revision:", metadata.get("revision"))
        print("PDF Page:", metadata.get("page_number"))

        print("\nContent:")
        print(document.page_content)

        # Verify machine isolation
        assert (
            metadata.get("machine_id") == machine_id
        ), "Cross-machine retrieval detected!"

    print("\nMachine isolation test passed!")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--machine", required=True, help="Machine ID")

    parser.add_argument("--question", required=True, help="Question to search")

    args = parser.parse_args()

    run_test(args.question, args.machine)
