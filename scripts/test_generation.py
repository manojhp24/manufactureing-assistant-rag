import argparse
from pprint import pprint

from rag.generation.answer_generator import generate_answer


def run_test(question, machine_id):

    print("\nMachine:", machine_id, flush=True)
    print("Question:", question, flush=True)

    print("\nCalling generate_answer()...", flush=True)

    result = generate_answer(question=question, machine_id=machine_id)

    print("\nGeneration completed!", flush=True)

    print("\n" + "=" * 60)
    print("GENERATED ANSWER")
    print("=" * 60)

    print(result["answer"])

    print("\nSTATUS:")
    print(result["status"])

    print("\nSOURCES:")
    pprint(result["sources"])

    print("\nEVIDENCE EVALUATION:")
    pprint(result["evaluation"])

    print("\nEVIDENCE EVALUATION:")
    pprint(result["evaluation"])


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("--machine", required=True)
    parser.add_argument("--question", required=True)

    args = parser.parse_args()

    run_test(question=args.question, machine_id=args.machine)
