# File: backend/app/schemas/evidence.py
"""Evidence response schema (what the API returns about a stored file)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceResponse(BaseModel):
    # Allows building the response straight from the ORM object.
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: int
    uploaded_at: datetime
