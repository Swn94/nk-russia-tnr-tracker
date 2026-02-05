"""Data models for TJWG FOOTPRINTS (NK Footprints 2.0) entities.

These models represent the data structures from the FOOTPRINTS database,
which documents cases of arbitrary detention, abduction, and enforced
disappearances committed by North Korea.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FootprintsVictimType(str, Enum):
    """Classification of victim types in FOOTPRINTS."""
    ABDUCTEE = "abductee"
    ABDUCTEE_SOUTH_KOREAN = "abductee_south_korean"
    ABDUCTEE_FOREIGN = "abductee_foreign"
    POW = "pow"  # Prisoner of War
    DEFECTOR = "defector"
    DETAINED = "detained"
    DISAPPEARED = "disappeared"
    FISHERMAN = "fisherman"
    CIVILIAN = "civilian"
    OTHER = "other"


class FootprintsPerpetratorType(str, Enum):
    """Classification of perpetrator types in FOOTPRINTS."""
    STATE_ORGAN = "state_organ"
    OFFICIAL = "official"
    MILITARY = "military"
    SECURITY_AGENCY = "security_agency"
    OTHER = "other"


class FootprintsPerpOrganization(str, Enum):
    """Known perpetrator organizations in FOOTPRINTS."""
    MSS = "mss"  # Ministry of State Security (국가보위성)
    MPS = "mps"  # Ministry of People's Security (사회안전성)
    KPA = "kpa"  # Korean People's Army (조선인민군)
    PARTY = "party"  # Workers' Party of Korea
    OTHER = "other"


class FootprintsProceedingType(str, Enum):
    """Types of legal proceedings in FOOTPRINTS."""
    UN_INQUIRY = "un_inquiry"
    UN_RESOLUTION = "un_resolution"
    ICC_REFERRAL = "icc_referral"
    DOMESTIC_COURT = "domestic_court"
    TRUTH_COMMISSION = "truth_commission"
    FAMILY_PETITION = "family_petition"
    NGO_REPORT = "ngo_report"
    OTHER = "other"


class FootprintsProceedingForum(str, Enum):
    """Legal forums in FOOTPRINTS."""
    UN_HRC = "un_hrc"  # UN Human Rights Council
    UN_GA = "un_ga"  # UN General Assembly
    ICC = "icc"  # International Criminal Court
    SOUTH_KOREAN_COURT = "south_korean_court"
    JAPANESE_COURT = "japanese_court"
    OTHER = "other"


class FootprintsVictimBase(BaseModel):
    """Base model for FOOTPRINTS victim records."""
    external_id: str = Field(..., description="UWAZI sharedId")
    name: str = Field(..., max_length=255)
    name_korean: Optional[str] = Field(None, max_length=255)
    name_original: Optional[str] = Field(None, max_length=255, description="Name in original language")
    victim_type: FootprintsVictimType = Field(default=FootprintsVictimType.OTHER)
    gender: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    age_at_incident: Optional[int] = Field(None, ge=0, le=150)
    nationality: Optional[str] = Field(None, max_length=100)
    occupation: Optional[str] = Field(None, max_length=255)
    residence: Optional[str] = Field(None, max_length=255)

    # Incident details
    date_of_incident: Optional[date] = None
    date_of_incident_end: Optional[date] = None
    place_of_incident: Optional[str] = Field(None, max_length=500)
    place_coordinates: Optional[tuple[float, float]] = None
    circumstances: Optional[str] = None

    # Current status
    last_known_location: Optional[str] = Field(None, max_length=500)
    current_status: Optional[str] = Field(None, max_length=255)
    date_of_release: Optional[date] = None
    date_of_death: Optional[date] = None

    # Relationships
    related_perpetrator_ids: list[str] = Field(default_factory=list)
    related_proceeding_ids: list[str] = Field(default_factory=list)
    related_victim_ids: list[str] = Field(default_factory=list)

    # Source information
    source_url: str = Field(..., max_length=500)
    source_urls: list[str] = Field(default_factory=list)
    testimonial_ids: list[str] = Field(default_factory=list)

    # Metadata
    metadata: dict = Field(default_factory=dict)
    language: str = Field(default="en", max_length=10)
    fetch_date: Optional[datetime] = None

    @field_validator('related_perpetrator_ids', 'related_proceeding_ids',
                     'related_victim_ids', 'source_urls', 'testimonial_ids', mode='before')
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


class FootprintsVictimCreate(FootprintsVictimBase):
    """Model for creating a new FOOTPRINTS victim record."""
    pass


class FootprintsVictim(FootprintsVictimBase):
    """Complete FOOTPRINTS victim model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FootprintsPerpetratorBase(BaseModel):
    """Base model for FOOTPRINTS perpetrator records."""
    external_id: str = Field(..., description="UWAZI sharedId")
    name: str = Field(..., max_length=255)
    name_korean: Optional[str] = Field(None, max_length=255)
    perpetrator_type: FootprintsPerpetratorType = Field(default=FootprintsPerpetratorType.OTHER)
    organization: Optional[FootprintsPerpOrganization] = None
    organization_name: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    rank: Optional[str] = Field(None, max_length=100)

    # Activity period
    period_active_start: Optional[date] = None
    period_active_end: Optional[date] = None
    period_description: Optional[str] = Field(None, max_length=500)

    # Accountability
    sanctioned: bool = Field(default=False)
    sanction_details: Optional[str] = None
    indicted: bool = Field(default=False)
    indictment_details: Optional[str] = None

    # Relationships
    related_victim_ids: list[str] = Field(default_factory=list)
    related_case_ids: list[str] = Field(default_factory=list)
    superior_ids: list[str] = Field(default_factory=list)
    subordinate_ids: list[str] = Field(default_factory=list)

    # Source information
    source_url: str = Field(..., max_length=500)
    source_urls: list[str] = Field(default_factory=list)

    # Metadata
    metadata: dict = Field(default_factory=dict)
    language: str = Field(default="en", max_length=10)
    fetch_date: Optional[datetime] = None

    @field_validator('related_victim_ids', 'related_case_ids',
                     'superior_ids', 'subordinate_ids', 'source_urls', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v


class FootprintsPerpetratorCreate(FootprintsPerpetratorBase):
    """Model for creating a new FOOTPRINTS perpetrator record."""
    pass


class FootprintsPerpetrator(FootprintsPerpetratorBase):
    """Complete FOOTPRINTS perpetrator model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FootprintsProceedingBase(BaseModel):
    """Base model for FOOTPRINTS legal proceeding records."""
    external_id: str = Field(..., description="UWAZI sharedId")
    title: str = Field(..., max_length=500)
    title_korean: Optional[str] = Field(None, max_length=500)
    proceeding_type: FootprintsProceedingType = Field(default=FootprintsProceedingType.OTHER)
    forum: Optional[FootprintsProceedingForum] = None
    forum_name: Optional[str] = Field(None, max_length=255)

    # Timeline
    date_initiated: Optional[date] = None
    date_concluded: Optional[date] = None
    status: Optional[str] = Field(None, max_length=100)
    outcome: Optional[str] = None

    # Details
    description: Optional[str] = None
    legal_basis: Optional[str] = None
    decision_text: Optional[str] = None

    # Relationships
    related_victim_ids: list[str] = Field(default_factory=list)
    related_perpetrator_ids: list[str] = Field(default_factory=list)

    # Documents
    document_urls: list[str] = Field(default_factory=list)
    document_titles: list[str] = Field(default_factory=list)

    # Source information
    source_url: str = Field(..., max_length=500)
    source_urls: list[str] = Field(default_factory=list)

    # Metadata
    metadata: dict = Field(default_factory=dict)
    language: str = Field(default="en", max_length=10)
    fetch_date: Optional[datetime] = None

    @field_validator('related_victim_ids', 'related_perpetrator_ids',
                     'document_urls', 'document_titles', 'source_urls', mode='before')
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        return v


class FootprintsProceedingCreate(FootprintsProceedingBase):
    """Model for creating a new FOOTPRINTS proceeding record."""
    pass


class FootprintsProceeding(FootprintsProceedingBase):
    """Complete FOOTPRINTS proceeding model with database fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FootprintsSyncStatus(BaseModel):
    """Status of FOOTPRINTS data synchronization."""
    last_sync_at: Optional[datetime] = None
    victims_count: int = 0
    perpetrators_count: int = 0
    proceedings_count: int = 0
    last_error: Optional[str] = None
    is_syncing: bool = False


class FootprintsSearchParams(BaseModel):
    """Search parameters for FOOTPRINTS entities."""
    query: Optional[str] = None
    entity_type: Optional[str] = None
    victim_type: Optional[FootprintsVictimType] = None
    perpetrator_org: Optional[FootprintsPerpOrganization] = None
    proceeding_forum: Optional[FootprintsProceedingForum] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    language: str = Field(default="en")
