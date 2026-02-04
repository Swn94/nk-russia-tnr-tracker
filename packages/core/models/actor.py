"""Actor model for perpetrators, victims, entities, witnesses, and officials."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ActorType(str, Enum):
    """Type of actor in the human rights tracking system."""
    PERPETRATOR = "perpetrator"
    VICTIM = "victim"
    ENTITY = "entity"
    WITNESS = "witness"
    OFFICIAL = "official"


class ActorBase(BaseModel):
    """Base actor model with common fields."""
    name: str = Field(..., max_length=255, description="Primary name")
    name_korean: Optional[str] = Field(None, max_length=255, description="Korean name")
    name_russian: Optional[str] = Field(None, max_length=255, description="Russian name")
    actor_type: ActorType = Field(..., description="Type of actor")
    nationality: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[date] = None
    aliases: Optional[list[str]] = Field(default_factory=list)
    description: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = Field(default_factory=dict)

    @field_validator('aliases', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v

    @field_validator('metadata', mode='before')
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


class ActorCreate(ActorBase):
    """Model for creating a new actor."""
    pass


class ActorUpdate(BaseModel):
    """Model for updating an existing actor."""
    name: Optional[str] = Field(None, max_length=255)
    name_korean: Optional[str] = Field(None, max_length=255)
    name_russian: Optional[str] = Field(None, max_length=255)
    actor_type: Optional[ActorType] = None
    nationality: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    date_of_birth: Optional[date] = None
    aliases: Optional[list[str]] = None
    description: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None


class Actor(ActorBase):
    """Complete actor model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChainOfCommand(BaseModel):
    """Relationship between superior and subordinate actors."""
    id: UUID
    superior_id: UUID
    subordinate_id: UUID
    relationship_type: str = Field(..., max_length=100)
    organization: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evidence_ids: Optional[list[UUID]] = Field(default_factory=list)
    confidence_score: Optional[float] = Field(0.5, ge=0, le=1)
    notes: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime

    @field_validator('evidence_ids', mode='before')
    @classmethod
    def ensure_uuid_list(cls, v):
        if v is None:
            return []
        return v

    @field_validator('metadata', mode='before')
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @field_validator('confidence_score', mode='before')
    @classmethod
    def ensure_float(cls, v):
        if v is None:
            return 0.5
        return float(v)

    class Config:
        from_attributes = True


class ChainOfCommandCreate(BaseModel):
    """Model for creating a chain of command relationship."""
    superior_id: UUID
    subordinate_id: UUID
    relationship_type: str = Field(..., max_length=100)
    organization: Optional[str] = Field(None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence_score: float = Field(0.5, ge=0, le=1)
    notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
