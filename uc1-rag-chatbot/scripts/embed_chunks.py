"""Create embeddings for chunks that do not have one yet.

Run from the backend folder, after load_sources.py:
    .venv\\Scripts\\python.exe ..\\scripts\\embed_chunks.py [--limit N]

Safe to stop and re-run: finished chunks are skipped.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.embeddings import EMBEDDING_MODEL, EmbeddingError, embed_texts  # noqa: E402
from app.models import Chunk, ChunkEmbedding  # noqa: E402

SAVE_EVERY = 100


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="embed at most this many chunks")
    limit = parser.parse_args().limit

    with SessionLocal() as session:
        done = select(ChunkEmbedding.chunk_id)
        todo = session.scalars(select(Chunk).where(Chunk.id.not_in(done)).order_by(Chunk.version_id, Chunk.ordinal)).all()
        if limit:
            todo = todo[:limit]
        print(f"{len(todo)} chunks to embed")
        try:
            for start in range(0, len(todo), SAVE_EVERY):
                batch = todo[start : start + SAVE_EVERY]
                vectors = embed_texts([c.text for c in batch])
                session.add_all(ChunkEmbedding(chunk_id=c.id, model=EMBEDDING_MODEL, vector=v) for c, v in zip(batch, vectors))
                session.commit()
                print(f"embedded {start + len(batch)} / {len(todo)}")
        except EmbeddingError as exc:
            print(f"stopped: {exc}. Run again to continue.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
