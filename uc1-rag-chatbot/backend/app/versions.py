"""Date-aware version lookup: which version of a document was in force on a given day."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DocumentVersion


def version_in_force(session: Session, document_id: uuid.UUID, as_of: date) -> DocumentVersion | None:
    """Return the version whose effective period contains `as_of`, or None.

    A version applies from `effective_from` (inclusive) up to `effective_to` (exclusive).
    An empty `effective_to` means the version is still in force. Drafts never apply.
    """
    stmt = (
        select(DocumentVersion)
        .where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.status != "draft",
            DocumentVersion.effective_from <= as_of,
            (DocumentVersion.effective_to.is_(None)) | (DocumentVersion.effective_to > as_of),
        )
        .order_by(DocumentVersion.effective_from.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()
