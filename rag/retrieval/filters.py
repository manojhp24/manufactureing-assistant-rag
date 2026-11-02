def machine_filter(machine_id: str) -> dict:
    if not machine_id or not machine_id.strip():
        raise ValueError("Machine ID is required.")

    return {"machine_id": machine_id.strip()}
