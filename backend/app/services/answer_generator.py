from backend.app.services.vector_store import VectorRecord


def generate_answer(query: str, records: list[VectorRecord]) -> str:
    if not records:
        return "No relevant context found."

    context = " ".join(record.text for record in records)
    return f"Answer based on retrieved context for '{query}': {context}"
