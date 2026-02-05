-- TJWG FOOTPRINTS (NK Footprints 2.0) Database Schema Extension
-- Extends the main schema with tables for FOOTPRINTS data
--
-- Source: https://nkfootprints.tjwg.org/en/library
-- Documentation: https://huridocs.org/resource-library/human-rights-research-databases/north-korea-footprints/

-- =============================================================================
-- ENUM TYPES FOR FOOTPRINTS
-- =============================================================================

-- Victim classification types
CREATE TYPE footprints_victim_type AS ENUM (
    'abductee',
    'abductee_south_korean',
    'abductee_foreign',
    'pow',
    'defector',
    'detained',
    'disappeared',
    'fisherman',
    'civilian',
    'other'
);

-- Perpetrator classification types
CREATE TYPE footprints_perpetrator_type AS ENUM (
    'state_organ',
    'official',
    'military',
    'security_agency',
    'other'
);

-- Known perpetrator organizations
CREATE TYPE footprints_perp_organization AS ENUM (
    'mss',      -- Ministry of State Security (국가보위성)
    'mps',      -- Ministry of People's Security (사회안전성)
    'kpa',      -- Korean People's Army (조선인민군)
    'party',    -- Workers' Party of Korea
    'other'
);

-- Legal proceeding types
CREATE TYPE footprints_proceeding_type AS ENUM (
    'un_inquiry',
    'un_resolution',
    'icc_referral',
    'domestic_court',
    'truth_commission',
    'family_petition',
    'ngo_report',
    'other'
);

-- Legal forums
CREATE TYPE footprints_proceeding_forum AS ENUM (
    'un_hrc',           -- UN Human Rights Council
    'un_ga',            -- UN General Assembly
    'icc',              -- International Criminal Court
    'south_korean_court',
    'japanese_court',
    'other'
);

-- =============================================================================
-- FOOTPRINTS VICTIMS TABLE
-- =============================================================================

CREATE TABLE footprints_victims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE NOT NULL,  -- UWAZI sharedId

    -- Identity
    name VARCHAR(255) NOT NULL,
    name_korean VARCHAR(255),
    name_original VARCHAR(255),
    victim_type footprints_victim_type DEFAULT 'other',
    gender VARCHAR(20),
    date_of_birth DATE,
    age_at_incident INTEGER CHECK (age_at_incident >= 0 AND age_at_incident <= 150),
    nationality VARCHAR(100),
    occupation VARCHAR(255),
    residence VARCHAR(255),

    -- Incident details
    date_of_incident DATE,
    date_of_incident_end DATE,
    place_of_incident VARCHAR(500),
    place_coordinates POINT,
    circumstances TEXT,

    -- Current status
    last_known_location VARCHAR(500),
    current_status VARCHAR(255),
    date_of_release DATE,
    date_of_death DATE,

    -- Relationships (stored as external IDs for linking)
    related_perpetrator_ids TEXT[],
    related_proceeding_ids TEXT[],
    related_victim_ids TEXT[],
    testimonial_ids TEXT[],

    -- Source information
    source_url VARCHAR(500) NOT NULL,
    source_urls TEXT[],

    -- Metadata
    metadata JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'en',
    fetch_date TIMESTAMP WITH TIME ZONE,

    -- Internal tracking
    linked_actor_id UUID REFERENCES actors(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- FOOTPRINTS PERPETRATORS TABLE
-- =============================================================================

CREATE TABLE footprints_perpetrators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE NOT NULL,  -- UWAZI sharedId

    -- Identity
    name VARCHAR(255) NOT NULL,
    name_korean VARCHAR(255),
    perpetrator_type footprints_perpetrator_type DEFAULT 'other',
    organization footprints_perp_organization,
    organization_name VARCHAR(255),
    position VARCHAR(255),
    rank VARCHAR(100),

    -- Activity period
    period_active_start DATE,
    period_active_end DATE,
    period_description VARCHAR(500),

    -- Accountability
    sanctioned BOOLEAN DEFAULT FALSE,
    sanction_details TEXT,
    indicted BOOLEAN DEFAULT FALSE,
    indictment_details TEXT,

    -- Relationships
    related_victim_ids TEXT[],
    related_case_ids TEXT[],
    superior_ids TEXT[],
    subordinate_ids TEXT[],

    -- Source information
    source_url VARCHAR(500) NOT NULL,
    source_urls TEXT[],

    -- Metadata
    metadata JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'en',
    fetch_date TIMESTAMP WITH TIME ZONE,

    -- Internal tracking
    linked_actor_id UUID REFERENCES actors(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- FOOTPRINTS PROCEEDINGS TABLE
-- =============================================================================

CREATE TABLE footprints_proceedings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE NOT NULL,  -- UWAZI sharedId

    -- Basic info
    title VARCHAR(500) NOT NULL,
    title_korean VARCHAR(500),
    proceeding_type footprints_proceeding_type DEFAULT 'other',
    forum footprints_proceeding_forum,
    forum_name VARCHAR(255),

    -- Timeline
    date_initiated DATE,
    date_concluded DATE,
    status VARCHAR(100),
    outcome TEXT,

    -- Details
    description TEXT,
    legal_basis TEXT,
    decision_text TEXT,

    -- Relationships
    related_victim_ids TEXT[],
    related_perpetrator_ids TEXT[],

    -- Documents
    document_urls TEXT[],
    document_titles TEXT[],

    -- Source information
    source_url VARCHAR(500) NOT NULL,
    source_urls TEXT[],

    -- Metadata
    metadata JSONB DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'en',
    fetch_date TIMESTAMP WITH TIME ZONE,

    -- Internal tracking
    linked_case_id UUID REFERENCES cases(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- FOOTPRINTS SYNC STATUS TABLE
-- =============================================================================

CREATE TABLE footprints_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    victims_synced INTEGER DEFAULT 0,
    perpetrators_synced INTEGER DEFAULT 0,
    proceedings_synced INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    sync_duration_seconds DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'idle',  -- idle, syncing, completed, failed
    last_error TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES FOR FOOTPRINTS TABLES
-- =============================================================================

-- Victims indexes
CREATE INDEX idx_fp_victims_external_id ON footprints_victims(external_id);
CREATE INDEX idx_fp_victims_type ON footprints_victims(victim_type);
CREATE INDEX idx_fp_victims_nationality ON footprints_victims(nationality);
CREATE INDEX idx_fp_victims_date ON footprints_victims(date_of_incident);
CREATE INDEX idx_fp_victims_name_search ON footprints_victims
    USING gin(to_tsvector('english', name || ' ' || COALESCE(name_korean, '')));
CREATE INDEX idx_fp_victims_linked_actor ON footprints_victims(linked_actor_id);

-- Perpetrators indexes
CREATE INDEX idx_fp_perps_external_id ON footprints_perpetrators(external_id);
CREATE INDEX idx_fp_perps_type ON footprints_perpetrators(perpetrator_type);
CREATE INDEX idx_fp_perps_org ON footprints_perpetrators(organization);
CREATE INDEX idx_fp_perps_name_search ON footprints_perpetrators
    USING gin(to_tsvector('english', name || ' ' || COALESCE(name_korean, '')));
CREATE INDEX idx_fp_perps_linked_actor ON footprints_perpetrators(linked_actor_id);

-- Proceedings indexes
CREATE INDEX idx_fp_procs_external_id ON footprints_proceedings(external_id);
CREATE INDEX idx_fp_procs_type ON footprints_proceedings(proceeding_type);
CREATE INDEX idx_fp_procs_forum ON footprints_proceedings(forum);
CREATE INDEX idx_fp_procs_date ON footprints_proceedings(date_initiated);
CREATE INDEX idx_fp_procs_title_search ON footprints_proceedings
    USING gin(to_tsvector('english', title || ' ' || COALESCE(title_korean, '')));
CREATE INDEX idx_fp_procs_linked_case ON footprints_proceedings(linked_case_id);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================================================

CREATE TRIGGER update_fp_victims_updated_at
    BEFORE UPDATE ON footprints_victims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fp_perpetrators_updated_at
    BEFORE UPDATE ON footprints_perpetrators
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fp_proceedings_updated_at
    BEFORE UPDATE ON footprints_proceedings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INSERT TJWG FOOTPRINTS DATA SOURCE
-- =============================================================================

INSERT INTO data_sources (name, source_type, base_url, sync_frequency_hours, metadata) VALUES
(
    'TJWG FOOTPRINTS',
    'uwazi_api',
    'https://nkfootprints.tjwg.org',
    168,  -- Weekly sync
    '{
        "description": "NK Footprints 2.0 - Joint civil society database documenting arbitrary detention, abduction, and enforced disappearances by North Korea",
        "platform": "UWAZI (HURIDOCS)",
        "partners": ["TJWG", "NKHR", "KWAFU", "JFNK"],
        "data_types": ["victims", "perpetrators", "proceedings", "testimonials"],
        "languages": ["en", "ko"],
        "api_version": "uwazi",
        "fallback_url": "https://nkfootprints.info"
    }'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    base_url = EXCLUDED.base_url,
    metadata = EXCLUDED.metadata,
    sync_frequency_hours = EXCLUDED.sync_frequency_hours;

-- =============================================================================
-- VIEWS FOR FOOTPRINTS DATA
-- =============================================================================

-- Unified view of all FOOTPRINTS victims with linked actors
CREATE OR REPLACE VIEW footprints_victims_full AS
SELECT
    fv.*,
    a.id AS actor_id,
    a.actor_type AS actor_category,
    a.organization AS actor_org
FROM footprints_victims fv
LEFT JOIN actors a ON fv.linked_actor_id = a.id;

-- Unified view of all FOOTPRINTS perpetrators with linked actors
CREATE OR REPLACE VIEW footprints_perpetrators_full AS
SELECT
    fp.*,
    a.id AS actor_id,
    a.position AS actor_position,
    cc.superior_id,
    cc.subordinate_id
FROM footprints_perpetrators fp
LEFT JOIN actors a ON fp.linked_actor_id = a.id
LEFT JOIN chain_of_command cc ON a.id = cc.subordinate_id OR a.id = cc.superior_id;

-- Summary statistics view
CREATE OR REPLACE VIEW footprints_stats AS
SELECT
    (SELECT COUNT(*) FROM footprints_victims) AS total_victims,
    (SELECT COUNT(*) FROM footprints_perpetrators) AS total_perpetrators,
    (SELECT COUNT(*) FROM footprints_proceedings) AS total_proceedings,
    (SELECT COUNT(*) FROM footprints_victims WHERE victim_type = 'abductee') AS abductees,
    (SELECT COUNT(*) FROM footprints_victims WHERE victim_type = 'pow') AS pows,
    (SELECT COUNT(*) FROM footprints_victims WHERE victim_type = 'defector') AS defectors,
    (SELECT COUNT(*) FROM footprints_perpetrators WHERE organization = 'mss') AS mss_perpetrators,
    (SELECT COUNT(*) FROM footprints_perpetrators WHERE organization = 'mps') AS mps_perpetrators,
    (SELECT COUNT(*) FROM footprints_proceedings WHERE forum = 'un_hrc') AS un_hrc_proceedings,
    (SELECT MAX(last_sync_at) FROM footprints_sync_status) AS last_sync;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE footprints_victims IS 'Victims documented in TJWG FOOTPRINTS database - abductees, POWs, defectors, detained individuals';
COMMENT ON TABLE footprints_perpetrators IS 'Perpetrators documented in TJWG FOOTPRINTS - state organs, officials, security agencies';
COMMENT ON TABLE footprints_proceedings IS 'Legal proceedings related to FOOTPRINTS cases - UN inquiries, court cases, petitions';
COMMENT ON TABLE footprints_sync_status IS 'Synchronization status tracking for FOOTPRINTS data import';

COMMENT ON COLUMN footprints_victims.external_id IS 'UWAZI sharedId - unique identifier in the FOOTPRINTS database';
COMMENT ON COLUMN footprints_victims.linked_actor_id IS 'Reference to actors table for unified tracking';
COMMENT ON COLUMN footprints_perpetrators.organization IS 'Perpetrator organization code (MSS=국가보위성, MPS=사회안전성, KPA=조선인민군)';
