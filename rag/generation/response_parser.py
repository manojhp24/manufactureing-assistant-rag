import json

from rag.generation.response_schema import RAGResponse


def extract_response_text(response):

    content = response.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text_parts = [
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]

        return "\n".join(text_parts)

    raise ValueError("Unsupported Gemini response format.")


def parse_response(response):

    response_text = extract_response_text(response)

    # Handle accidental Markdown code fences
    response_text = response_text.strip()

    if response_text.startswith("```"):
        response_text = response_text.replace("```json", "", 1)
        response_text = response_text.replace("```", "").strip()

    # Extract JSON object
    start = response_text.find("{")
    end = response_text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Gemini did not return a JSON object.")

    json_text = response_text[start : end + 1]

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid JSON.") from exc

    try:
        validated = RAGResponse.model_validate(parsed)
    except Exception as exc:
        raise ValueError("Gemini response failed schema validation.") from exc

    return validated.model_dump()
