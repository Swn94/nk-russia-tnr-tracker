-- NK-Russia Human Rights Chain of Command Tracker
-- Database Schema v1.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE actor_type AS ENUM ('perpetrator', 'victim', 'entity', 'witness', 'official');
CREATE TYPE case_status AS ENUM ('open', 'under_investigation', 'documented', 'closed', 'archived');
CREATE TYPE evidence_type AS ENUM ('document', 'testimony', 'media', 'satellite', 'financial', 'communication');
CREATE TYPE sanction_status AS ENUM ('candidate', 'proposed', 'under_review', 'sanctioned', 'rejected');
CREATE TYPE tnr_type AS ENUM ('direct_attack', 'co_opting', 'mobility_controls', 'threats_from_distance');

-- Actors table (perpetrators, victims, entities)
CREATE TABLE actors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    name_korean VARCHAR(255),
    name_russian VARCHAR(255),
    actor_type actor_type NOT NULL,
    nationality VARCHAR(100),
    organization VARCHAR(255),
    position VARCHAR(255),
    date_of_birth DATE,
    aliases TEXT[],
    description TEXT,
    photo_url VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Cases table (human rights violation cases)
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    title_korean VARCHAR(500),
    case_number VARCHAR(100) UNIQUE,
    status case_status DEFAULT 'open',
    tnr_type tnr_type,
    date_occurred DATE,
    date_reported DATE,
    location VARCHAR(255),
    location_coordinates POINT,
    country VARCHAR(100),
    summary TEXT,
    details TEXT,
    source_urls TEXT[],
    tags TEXT[],
    severity_score INTEGER CHECK (severity_score >= 1 AND severity_score <= 10),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Evidence table
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    evidence_type evidence_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    source_name VARCHAR(255),
    source_url VARCHAR(500),
    file_path VARCHAR(500),
    file_hash VARCHAR(128),
    date_obtained DATE,
    date_created DATE,
    authenticity_score DECIMAL(3,2) CHECK (authenticity_score >= 0 AND authenticity_score <= 1),
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(255),
    verification_date DATE,
    raw_content TEXT,
    processed_content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sanctions candidates table
CREATE TABLE sanctions_candidates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID REFERENCES actors(id) ON DELETE CASCADE,
    status sanction_status DEFAULT 'candidate',
    recommendation_date DATE,
    proposed_sanctions TEXT[],
    legal_basis TEXT,
    supporting_cases UUID[],
    evidence_strength_score DECIMAL(3,2) CHECK (evidence_strength_score >= 0 AND evidence_strength_score <= 1),
    priority_level INTEGER CHECK (priority_level >= 1 AND priority_level <= 5),
    reviewing_body VARCHAR(255),
    decision_date DATE,
    decision_notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chain of command relationships
CREATE TABLE chain_of_command (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    superior_id UUID REFERENCES actors(id) ON DELETE CASCADE,
    subordinate_id UUID REFERENCES actors(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    organization VARCHAR(255),
    start_date DATE,
    end_date DATE,
    evidence_ids UUID[],
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(superior_id, subordinate_id, organization)
);

-- Case-Actor relationships (many-to-many)
CREATE TABLE case_actors (
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES actors(id) ON DELETE CASCADE,
    role VARCHAR(100) NOT NULL,
    description TEXT,
    PRIMARY KEY (case_id, actor_id, role)
);

-- Data sources tracking
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    source_type VARCHAR(100),
    base_url VARCHAR(500),
    api_key_env_var VARCHAR(100),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_frequency_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ETL job logs
CREATE TABLE etl_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES data_sources(id),
    job_type VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50),
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_actors_type ON actors(actor_type);
CREATE INDEX idx_actors_nationality ON actors(nationality);
CREATE INDEX idx_actors_name_search ON actors USING gin(to_tsvector('english', name || ' ' || COALESCE(name_korean, '') || ' ' || COALESCE(name_russian, '')));

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_tnr_type ON cases(tnr_type);
CREATE INDEX idx_cases_date ON cases(date_occurred);
CREATE INDEX idx_cases_country ON cases(country);
CREATE INDEX idx_cases_search ON cases USING gin(to_tsvector('english', title || ' ' || COALESCE(summary, '')));

CREATE INDEX idx_evidence_case ON evidence(case_id);
CREATE INDEX idx_evidence_type ON evidence(evidence_type);
CREATE INDEX idx_evidence_verified ON evidence(is_verified);

CREATE INDEX idx_sanctions_status ON sanctions_candidates(status);
CREATE INDEX idx_sanctions_actor ON sanctions_candidates(actor_id);

CREATE INDEX idx_chain_superior ON chain_of_command(superior_id);
CREATE INDEX idx_chain_subordinate ON chain_of_command(subordinate_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_actors_updated_at BEFORE UPDATE ON actors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cases_updated_at BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sanctions_updated_at BEFORE UPDATE ON sanctions_candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial data sources
INSERT INTO data_sources (name, source_type, base_url, api_key_env_var, sync_frequency_hours) VALUES
    ('data.go.kr', 'api', 'https://apis.data.go.kr/1250000/prsn', 'DATA_GO_KR_API_KEY', 24),
    ('HUDOC', 'web_scraping', 'https://hudoc.echr.coe.int', NULL, 168),
    ('Freedom House', 'web_scraping', 'https://freedomhouse.org/report/transnational-repression', NULL, 720),
    ('UN OHCHR', 'web_scraping', 'https://www.ohchr.org', NULL, 168),
    ('ICC', 'web_scraping', 'https://www.icc-cpi.int', NULL, 168),
    ('OSCE', 'web_scraping', 'https://www.osce.org', NULL, 168);
