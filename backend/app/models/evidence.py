# File: backend/app/models/evidence.py
"""
Evidence model.

WHY: Every uploaded file becomes immutable evidence. The SHA-256 hash is
the integrity anchor: if the stored file is ever altered, its recomputed
hash will not match, which is the basis of chain-of-custody. We store the
stored (sanitized) path separately from the original filename so a
malicious filename can never influence where the file lands on disk.
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # The name the user supplied. Display-only; never used for disk paths.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # The sanitized, server-generated path where the file is actually stored.
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Declared MIME type, validated on upload.
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)

    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Integrity anchor. 64 hex chars for SHA-256.
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Text extracted from the file via OCR/parsing. Nullable because
    # extraction is run async or some files might contain no readable text.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped["Case"] = relationship(back_populates="evidence")  # noqa: F821
