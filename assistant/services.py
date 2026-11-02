
from rag.generation.answer_generator import generate_answer


def ask_manual_assistant(question, machine_id):
    result = generate_answer(
        question=question,
        machine_id=machine_id
    )

    return result
