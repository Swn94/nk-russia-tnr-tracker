"""Case model for human rights violation cases."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """Status of a human rights case."""
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    DOCUMENTED = "documented"
    CLOSED = "closed"
    ARCHIVED = "archived"


class TNRType(str, Enum):
    """Transnational Repression type categories (Freedom House framework)."""
    DIRECT_ATTACK = "direct_attack"
    CO_OPTING = "co_opting"
    MOBILITY_CONTROLS = "mobility_controls"
    THREATS_FROM_DISTANCE = "threats_from_distance"


class CaseBase(BaseModel):
    """Base case model with common fields."""
    title: str = Field(..., max_length=500)
    title_korean: Optional[str] = Field(None, max_length=500)
    case_number: Optional[str] = Field(None, max_length=100)
    status: CaseStatus = Field(default=CaseStatus.OPEN)
    tnr_type: Optional[TNRType] = None
    date_occurred: Optional[date] = None
    date_reported: Optional[date] = None
    location: Optional[str] = Field(None, max_length=255)
    location_coordinates: Optional[tuple[float, float]] = None
    country: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = None
    details: Optional[str] = None
    source_urls: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    severity_score: Optional[int] = Field(None, ge=1, le=10)
    metadata: dict = Field(default_factory=dict)


class CaseCreate(CaseBase):
    """Model for creating a new case."""
    pass


class CaseUpdate(BaseModel):
    """Model for updating an existing case."""
    title: Optional[str] = Field(None, max_length=500)
    title_korean: Optional[str] = Field(None, max_length=500)
    case_number: Optional[str] = Field(None, max_length=100)
    status: Optional[CaseStatus] = None
    tnr_type: Optional[TNRType] = None
    date_occurred: Optional[date] = None
    date_reported: Optional[date] = None
    location: Optional[str] = Field(None, max_length=255)
    location_coordinates: Optional[tuple[float, float]] = None
    country: Optional[str] = Field(None, max_length=100)
    summary: Optional[str] = None
    details: Optional[str] = None
    source_urls: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    severity_score: Optional[int] = Field(None, ge=1, le=10)
    metadata: Optional[dict] = None


class Case(CaseBase):
    """Complete case model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseActor(BaseModel):
    """Association between a case and an actor."""
    case_id: UUID
    actor_id: UUID
    role: str = Field(..., max_length=100)
    description: Optional[str] = None

    class Config:
        from_attributes = True


class CaseSearch(BaseModel):
    """Search parameters for cases."""
    query: Optional[str] = None
    status: Optional[CaseStatus] = None
    tnr_type: Optional[TNRType] = None
    country: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    tags: Optional[list[str]] = None
    min_severity: Optional[int] = Field(None, ge=1, le=10)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
