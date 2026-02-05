-- data.go.kr (Korean Government Open Data) Database Schema Extension
-- North Korean Defector Statistics from Ministry of Unification
--
-- API: https://apis.data.go.kr/1250000/prsn
-- Endpoints: getPrsnYear, getPrsnAge, getPrsnOccup, getPrsnArea

-- =============================================================================
-- STATISTICS TABLES
-- =============================================================================

-- Yearly defector arrival statistics
CREATE TABLE IF NOT EXISTS defector_stats_yearly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year INTEGER NOT NULL,
    total INTEGER NOT NULL DEFAULT 0,
    male INTEGER DEFAULT 0,
    female INTEGER DEFAULT 0,
    cumulative_total INTEGER DEFAULT 0,
    source_url VARCHAR(500) DEFAULT 'https://apis.data.go.kr/1250000/prsn/getPrsnYear',
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year)
);

-- Age group distribution statistics
CREATE TABLE IF NOT EXISTS defector_stats_age (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    age_group VARCHAR(50) NOT NULL,
    age_min INTEGER,
    age_max INTEGER,
    count INTEGER NOT NULL DEFAULT 0,
    percentage DECIMAL(5,2),
    as_of_date DATE,
    source_url VARCHAR(500) DEFAULT 'https://apis.data.go.kr/1250000/prsn/getPrsnAge',
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(age_group, as_of_date)
);

-- Occupation distribution statistics
CREATE TABLE IF NOT EXISTS defector_stats_occupation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    occupation VARCHAR(100) NOT NULL,
    occupation_korean VARCHAR(100),
    count INTEGER NOT NULL DEFAULT 0,
    percentage DECIMAL(5,2),
    as_of_date DATE,
    source_url VARCHAR(500) DEFAULT 'https://apis.data.go.kr/1250000/prsn/getPrsnOccup',
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(occupation, as_of_date)
);

-- Origin region (North Korean provinces) statistics
CREATE TABLE IF NOT EXISTS defector_stats_region (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    region VARCHAR(100) NOT NULL,
    region_korean VARCHAR(100),
    count INTEGER NOT NULL DEFAULT 0,
    percentage DECIMAL(5,2),
    as_of_date DATE,
    source_url VARCHAR(500) DEFAULT 'https://apis.data.go.kr/1250000/prsn/getPrsnArea',
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region, as_of_date)
);

-- =============================================================================
-- MAPPING TABLE: Connect Statistics to Individual Cases
-- =============================================================================

-- Links defector statistics context to FOOTPRINTS victims or actors
CREATE TABLE IF NOT EXISTS defector_case_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Can link to multiple entity types
    footprints_victim_id UUID REFERENCES footprints_victims(id) ON DELETE SET NULL,
    actor_id UUID REFERENCES actors(id) ON DELETE SET NULL,

    -- Demographic context from statistics
    arrival_year INTEGER,
    age_group VARCHAR(50),
    occupation VARCHAR(100),
    origin_region VARCHAR(100),

    -- Mapping confidence
    mapping_confidence DECIMAL(3,2) CHECK (mapping_confidence >= 0 AND mapping_confidence <= 1),
    mapping_method VARCHAR(50),  -- 'manual', 'rule_based', 'ml_predicted'

    -- Notes
    notes TEXT,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- AGGREGATED STATISTICS VIEW
-- =============================================================================

CREATE OR REPLACE VIEW defector_stats_summary AS
SELECT
    (SELECT SUM(total) FROM defector_stats_yearly) AS total_defectors_all_time,
    (SELECT SUM(male) FROM defector_stats_yearly) AS total_male,
    (SELECT SUM(female) FROM defector_stats_yearly) AS total_female,
    (SELECT year FROM defector_stats_yearly ORDER BY year DESC LIMIT 1) AS latest_year,
    (SELECT total FROM defector_stats_yearly ORDER BY year DESC LIMIT 1) AS latest_year_count,
    (SELECT COUNT(*) FROM defector_stats_age) AS age_categories,
    (SELECT COUNT(*) FROM defector_stats_occupation) AS occupation_categories,
    (SELECT COUNT(*) FROM defector_stats_region) AS region_categories,
    (SELECT MAX(created_at) FROM defector_stats_yearly) AS last_updated;

-- Cross-reference view with FOOTPRINTS data
CREATE OR REPLACE VIEW defector_footprints_crossref AS
SELECT
    fv.id AS footprints_victim_id,
    fv.name,
    fv.victim_type,
    fv.date_of_incident,
    EXTRACT(YEAR FROM fv.date_of_incident) AS incident_year,
    dsy.total AS yearly_total_context,
    dcm.mapping_confidence
FROM footprints_victims fv
LEFT JOIN defector_case_mapping dcm ON fv.id = dcm.footprints_victim_id
LEFT JOIN defector_stats_yearly dsy ON dcm.arrival_year = dsy.year
WHERE fv.victim_type IN ('defector', 'detained', 'disappeared');

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_defector_yearly_year ON defector_stats_yearly(year);
CREATE INDEX IF NOT EXISTS idx_defector_age_group ON defector_stats_age(age_group);
CREATE INDEX IF NOT EXISTS idx_defector_occupation ON defector_stats_occupation(occupation);
CREATE INDEX IF NOT EXISTS idx_defector_region ON defector_stats_region(region);
CREATE INDEX IF NOT EXISTS idx_mapping_victim ON defector_case_mapping(footprints_victim_id);
CREATE INDEX IF NOT EXISTS idx_mapping_actor ON defector_case_mapping(actor_id);
CREATE INDEX IF NOT EXISTS idx_mapping_year ON defector_case_mapping(arrival_year);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER update_defector_yearly_updated_at
    BEFORE UPDATE ON defector_stats_yearly
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_defector_age_updated_at
    BEFORE UPDATE ON defector_stats_age
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_defector_occupation_updated_at
    BEFORE UPDATE ON defector_stats_occupation
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_defector_region_updated_at
    BEFORE UPDATE ON defector_stats_region
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_defector_mapping_updated_at
    BEFORE UPDATE ON defector_case_mapping
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE defector_stats_yearly IS 'Yearly North Korean defector arrival statistics from Ministry of Unification';
COMMENT ON TABLE defector_stats_age IS 'Age group distribution of North Korean defectors';
COMMENT ON TABLE defector_stats_occupation IS 'Occupation distribution of North Korean defectors before defection';
COMMENT ON TABLE defector_stats_region IS 'Origin region (North Korean provinces) distribution of defectors';
COMMENT ON TABLE defector_case_mapping IS 'Links statistical context to individual FOOTPRINTS cases or actors';
