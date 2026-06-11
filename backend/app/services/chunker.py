import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_length:
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_markdown(text: str, max_chunk_size: int = 1500, overlap: int = 100) -> list[str]:
    """Split markdown by headings, merge small sections, split large ones."""
    if not text:
        return []

    sections = _split_by_headings(text)
    chunks: list[str] = []

    buffer = ""
    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(buffer) + len(section) + 2 <= max_chunk_size:
            buffer = f"{buffer}\n\n{section}".strip() if buffer else section
        else:
            if buffer:
                chunks.extend(_split_large_section(buffer, max_chunk_size, overlap))
            buffer = section

    if buffer:
        chunks.extend(_split_large_section(buffer, max_chunk_size, overlap))

    return [chunk for chunk in chunks if chunk.strip()]


def _split_by_headings(text: str) -> list[str]:
    parts = re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE)
    return [part for part in parts if part.strip()]


def _split_large_section(section: str, max_size: int, overlap: int) -> list[str]:
    if len(section) <= max_size:
        return [section]

    chunks: list[str] = []
    paragraphs = re.split(r"\n{2,}", section)

    heading_prefix = ""
    if paragraphs and re.match(r"^#{1,3} ", paragraphs[0]):
        heading_prefix = paragraphs[0]
        paragraphs = paragraphs[1:]

    buffer = ""
    first_chunk = True

    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_size:
            buffer = candidate
        else:
            if buffer:
                if first_chunk and heading_prefix:
                    buffer = f"{heading_prefix}\n\n{buffer}"
                    first_chunk = False
                chunks.append(buffer)
            if len(paragraph) > max_size:
                sub_chunks = _hard_split(paragraph, max_size, overlap)
                if first_chunk and heading_prefix and sub_chunks:
                    sub_chunks[0] = f"{heading_prefix}\n\n{sub_chunks[0]}"
                    first_chunk = False
                chunks.extend(sub_chunks)
                buffer = ""
            else:
                buffer = paragraph

    if buffer:
        if first_chunk and heading_prefix:
            buffer = f"{heading_prefix}\n\n{buffer}"
        chunks.append(buffer)

    return chunks


def _hard_split(text: str, max_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
