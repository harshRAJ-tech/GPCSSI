# File: backend/app/services/evidence_storage.py
"""
Secure evidence storage.

WHY: File upload is one of the highest-risk surfaces in any web app. This
module enforces, in order:

1. A content-type allowlist (reject anything we do not expect).
2. A streamed write with a running byte counter, so an oversized file is
   rejected mid-stream and never fully buffered in memory (DoS guard).
3. A SHA-256 computed in the same single pass (integrity anchor).
4. A SERVER-generated UUID filename under a resolved upload directory,
   with a containment check, so a malicious original filename can never
   cause path traversal (the user's name is only kept for display).

If anything fails, the partially written file is removed so we never
leave orphaned or half-written evidence on disk.
"""
import hashlib
import os
import uuid
from dataclasses import dataclass

from fastapi import UploadFile

from app.core.config import settings

# Allowlist of accepted MIME types for the prototype.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

# Read the upload in fixed-size chunks (64 KiB) rather than all at once.
_CHUNK_SIZE = 64 * 1024


class UnsupportedFileType(Exception):
    """Raised when the uploaded content type is not in the allowlist."""


class FileTooLarge(Exception):
    """Raised when the upload exceeds MAX_UPLOAD_BYTES."""


@dataclass
class StoredFile:
    stored_path: str
    sha256: str
    size_bytes: int


def _upload_root() -> str:
    """Return the absolute, real upload directory, creating it if needed."""
    root = os.path.realpath(settings.UPLOAD_DIR)
    os.makedirs(root, exist_ok=True)
    return root


async def store_upload(upload: UploadFile) -> StoredFile:
    """Validate and persist an uploaded file securely."""
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileType(upload.content_type or "unknown")

    root = _upload_root()

    # Server-generated name. The user's filename never touches the path.
    stored_name = uuid.uuid4().hex
    stored_path = os.path.join(root, stored_name)

    # Defense in depth: prove the resolved path stays inside the root.
    if os.path.commonpath([root, os.path.realpath(stored_path)]) != root:
        raise RuntimeError("Resolved storage path escaped the upload root")

    hasher = hashlib.sha256()
    size = 0

    try:
        with open(stored_path, "wb") as out:
            while chunk := await upload.read(_CHUNK_SIZE):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_BYTES:
                    raise FileTooLarge(size)
                hasher.update(chunk)
                out.write(chunk)
    except BaseException:
        # Never leave a partial/orphaned file behind on any failure.
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise

    return StoredFile(stored_path=stored_path, sha256=hasher.hexdigest(), size_bytes=size)
