"""Evidence model for documentation and proof materials."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """Type of evidence collected."""
    DOCUMENT = "document"
    TESTIMONY = "testimony"
    MEDIA = "media"
    SATELLITE = "satellite"
    FINANCIAL = "financial"
    COMMUNICATION = "communication"


class EvidenceBase(BaseModel):
    """Base evidence model with common fields."""
    case_id: Optional[UUID] = None
    evidence_type: EvidenceType
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    source_name: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)
    file_hash: Optional[str] = Field(None, max_length=128)
    date_obtained: Optional[date] = None
    date_created: Optional[date] = None
    authenticity_score: Optional[float] = Field(None, ge=0, le=1)
    is_verified: bool = False
    verified_by: Optional[str] = Field(None, max_length=255)
    verification_date: Optional[date] = None
    raw_content: Optional[str] = None
    processed_content: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class EvidenceCreate(EvidenceBase):
    """Model for creating new evidence."""
    pass


class EvidenceUpdate(BaseModel):
    """Model for updating existing evidence."""
    case_id: Optional[UUID] = None
    evidence_type: Optional[EvidenceType] = None
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    source_name: Optional[str] = Field(None, max_length=255)
    source_url: Optional[str] = Field(None, max_length=500)
    file_path: Optional[str] = Field(None, max_length=500)
    file_hash: Optional[str] = Field(None, max_length=128)
    date_obtained: Optional[date] = None
    date_created: Optional[date] = None
    authenticity_score: Optional[float] = Field(None, ge=0, le=1)
    is_verified: Optional[bool] = None
    verified_by: Optional[str] = Field(None, max_length=255)
    verification_date: Optional[date] = None
    raw_content: Optional[str] = None
    processed_content: Optional[str] = None
    metadata: Optional[dict] = None


class Evidence(EvidenceBase):
    """Complete evidence model with database fields."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SanctionStatus(str, Enum):
    """Status of a sanctions candidate."""
    CANDIDATE = "candidate"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    SANCTIONED = "sanctioned"
    REJECTED = "rejected"


class SanctionsCandidateBase(BaseModel):
    """Base model for sanctions candidates."""
    actor_id: UUID
    status: SanctionStatus = Field(default=SanctionStatus.CANDIDATE)
    recommendation_date: Optional[date] = None
    proposed_sanctions: list[str] = Field(default_factory=list)
    legal_basis: Optional[str] = None
    supporting_cases: list[UUID] = Field(default_factory=list)
    evidence_strength_score: Optional[float] = Field(None, ge=0, le=1)
    priority_level: Optional[int] = Field(None, ge=1, le=5)
    reviewing_body: Optional[str] = Field(None, max_length=255)
    decision_date: Optional[date] = None
    decision_notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class SanctionsCandidateCreate(SanctionsCandidateBase):
    """Model for creating a new sanctions candidate."""
    pass


class SanctionsCandidate(SanctionsCandidateBase):
    """Complete sanctions candidate model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
