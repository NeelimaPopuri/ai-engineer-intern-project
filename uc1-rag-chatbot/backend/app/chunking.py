"""Structure-aware chunking.

Documents are split at their own headings (Article, Section, Chapter, Annex or a
markdown heading) so a citation can point to a real part of the source. A section
that is too long is split further at paragraph boundaries, with a small overlap so
a sentence that straddles two chunks is still found by search.
"""

import re
from dataclasses import dataclass

# Rough rule of thumb: one token is about four characters of English text.
CHARS_PER_TOKEN = 4

_HEADING = re.compile(
    r"^(?:#{1,4}\s+.+|(?:Article|Section|Chapter|Annex|Recital)\s+[\w.()-]+.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkData:
    ordinal: int
    section_ref: str | None
    text: str
    token_count: int


def estimate_tokens(text: str) -> int:
    """Cheap token estimate. Good enough for sizing chunks, not for billing."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_sections(text: str) -> list[tuple[str | None, str]]:
    """Return (heading, body) pairs. Text before the first heading has heading None."""
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and _HEADING.match(stripped) and len(stripped) <= 200:
            sections.append((stripped.lstrip("# ").strip(), []))
        else:
            sections[-1][1].append(line)
    return [(heading, "\n".join(body).strip()) for heading, body in sections if "\n".join(body).strip()]


def _split_long(body: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split one long section at paragraph breaks, carrying a short overlap forward."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    pieces: list[str] = []
    current = ""
    for para in paragraphs:
        # A single paragraph larger than the limit is cut at sentence ends, then by length.
        parts = [para] if len(para) <= max_chars else _cut_paragraph(para, max_chars)
        for part in parts:
            if current and len(current) + len(part) + 2 > max_chars:
                pieces.append(current)
                tail = current[-overlap_chars:] if overlap_chars else ""
                current = (tail + "\n\n" + part).strip() if tail else part
            else:
                current = f"{current}\n\n{part}".strip() if current else part
    if current:
        pieces.append(current)
    return pieces


def _cut_paragraph(para: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", para)
    out: list[str] = []
    current = ""
    for sentence in sentences:
        while len(sentence) > max_chars:  # no sentence break available: hard cut
            if current:
                out.append(current)
                current = ""
            out.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if current and len(current) + len(sentence) + 1 > max_chars:
            out.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current:
        out.append(current)
    return out


def chunk_text(text: str, max_tokens: int = 350, overlap_tokens: int = 40) -> list[ChunkData]:
    """Split `text` into chunks of at most about `max_tokens` tokens each."""
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if not 0 <= overlap_tokens < max_tokens:
        raise ValueError("overlap_tokens must be between 0 and max_tokens - 1")
    max_chars = max_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    chunks: list[ChunkData] = []
    for heading, body in _split_sections(text):
        pieces = [body] if len(body) <= max_chars else _split_long(body, max_chars, overlap_chars)
        for piece in pieces:
            chunks.append(ChunkData(len(chunks), heading, piece, estimate_tokens(piece)))
    return chunks
