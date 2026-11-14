from app.schemas.document import ChunkingStrategy


def _validate_chunk_size(chunk_size: int) -> None:
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1.")


def _fixed_size_chunks(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be at least 0 and smaller than chunk_size.")

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def _split_long_paragraph(paragraph: str, chunk_size: int) -> list[str]:
    pieces: list[str] = []
    remaining = paragraph.strip()
    separators = ("\n", ". ", " ")

    while len(remaining) > chunk_size:
        best_position = 0
        best_end = 0

        for separator in separators:
            position = remaining.rfind(separator, 0, chunk_size)
            if (
                position > best_position
                and position + len(separator) <= chunk_size
            ):
                best_position = position
                best_end = position + len(separator)

        boundary = best_end or chunk_size
        piece = remaining[:boundary].strip()

        if piece:
            pieces.append(piece)

        remaining = remaining[boundary:].strip()

    if remaining:
        pieces.append(remaining)

    return pieces


def _recursive_paragraph_chunks(text: str, chunk_size: int) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]

    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(_split_long_paragraph(paragraph, chunk_size))

    chunks: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = unit

    if current:
        chunks.append(current)

    return chunks


def chunk_text(
    text: str,
    strategy: ChunkingStrategy,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    _validate_chunk_size(chunk_size)
    cleaned_text = text.strip()

    if not cleaned_text:
        return []

    if strategy is ChunkingStrategy.FIXED_SIZE:
        return _fixed_size_chunks(cleaned_text, chunk_size, overlap)

    if strategy is ChunkingStrategy.RECURSIVE_PARAGRAPH:
        return _recursive_paragraph_chunks(cleaned_text, chunk_size)

    raise ValueError(f"Unsupported chunking strategy: {strategy}")