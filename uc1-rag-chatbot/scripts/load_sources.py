"""Load the collected source library into the database.

Run from the backend folder, after `alembic upgrade head`:
    .venv\\Scripts\\python.exe ..\\scripts\\load_sources.py

Reads data/sources.csv, orders each document's versions by effective date, and ingests them
so older versions are closed when a newer one takes effect. Safe to run again.
"""

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal  # noqa: E402
from app.ingestion import IngestionError, ingest_document_version  # noqa: E402


def main() -> int:
    with (ROOT / "data" / "sources.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda r: (r["document_title"], r["effective_from"]))

    failed = 0
    with SessionLocal() as session:
        for row in rows:
            text = (ROOT / "data" / "sources" / f"{row['slug']}.txt").read_text(encoding="utf-8")
            try:
                version = ingest_document_version(
                    session,
                    title=row["document_title"],
                    document_type=row["document_type"],
                    jurisdiction=row["jurisdiction"],
                    text=text,
                    effective_from=date.fromisoformat(row["effective_from"]),
                    publisher=row["publisher"],
                    source_url=row["url"],
                )
                print(f"loaded  {row['slug']}  version {version.version_number}")
            except IngestionError as exc:
                failed += 1
                print(f"failed  {row['slug']}: {exc}")
        session.commit()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
