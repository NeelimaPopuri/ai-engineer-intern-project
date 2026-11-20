"""Copy the stored vectors to Pinecone.

Run from the backend folder, after the vectors exist (load_sources.py and embed_chunks.py) and
after PINECONE_API_KEY and PINECONE_INDEX_HOST are set in .env:
    .venv\\Scripts\\python.exe ..\\scripts\\sync_pinecone.py

Safe to repeat. Run it again after ingesting a new document version, because closing the old
version changes its end date.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.pinecone_index import PineconeClient, PineconeError, sync_to_pinecone  # noqa: E402


def main() -> int:
    try:
        client = PineconeClient()
        with SessionLocal() as session:
            sent = sync_to_pinecone(session, client)
    except PineconeError as exc:
        print(f"stopped: {exc}")
        return 1
    print(f"upserted {sent} vectors into namespace '{client.namespace}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
