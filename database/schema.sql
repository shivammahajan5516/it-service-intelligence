-- =============================================================================
-- schema.sql  -  IT Service Intelligence Platform (synthetic data)
--
-- Pipeline:  data/raw/*.csv  ->  staging.*  ->  clean.*  ->  analytics.* (views)
--
--   staging   : exact copy of the CSV files. Every column is TEXT so that no
--               row is rejected on load; bad values are dealt with in clean.
--   clean     : typed, standardised, de-duplicated tables with data-quality
--               flags. Keys and CHECK constraints are added afterwards by
--               constraints.sql (faster bulk load, clearer error messages).
--   analytics : views that implement the business rules / KPI definitions
--               once (analytics_views.sql). The API and Power BI read these.
--   audit     : load log and row-level data-quality issue register.
--
-- Re-runnable: drops and recreates the four schemas.
-- =============================================================================

DROP SCHEMA IF EXISTS analytics CASCADE;
DROP SCHEMA IF EXISTS clean     CASCADE;
DROP SCHEMA IF EXISTS staging   CASCADE;
DROP SCHEMA IF EXISTS audit     CASCADE;

CREATE SCHEMA staging;
CREATE SCHEMA clean;
CREATE SCHEMA analytics;
CREATE SCHEMA audit;

COMMENT ON SCHEMA staging   IS 'Raw CSV extract, all TEXT, loaded as received';
COMMENT ON SCHEMA clean     IS 'Typed, standardised, de-duplicated data with DQ flags';
COMMENT ON SCHEMA analytics IS 'Business-rule views: single definition of every KPI';
COMMENT ON SCHEMA audit     IS 'Pipeline load log and data-quality issue register';

-- -----------------------------------------------------------------------------
-- Helper functions: safe casts that return NULL instead of failing the load
-- -----------------------------------------------------------------------------
CREATE FUNCTION clean.try_timestamp(p text) RETURNS timestamp
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN NULLIF(trim(p), '')::timestamp;
EXCEPTION WHEN others THEN
    RETURN NULL;
END $$;

CREATE FUNCTION clean.try_numeric(p text) RETURNS numeric
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    RETURN NULLIF(trim(p), '')::numeric;
EXCEPTION WHEN others THEN
    RETURN NULL;
END $$;

CREATE FUNCTION clean.try_bool(p text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE lower(trim(p))
               WHEN 'true' THEN TRUE  WHEN 't' THEN TRUE  WHEN 'yes' THEN TRUE  WHEN '1' THEN TRUE
               WHEN 'false' THEN FALSE WHEN 'f' THEN FALSE WHEN 'no' THEN FALSE  WHEN '0' THEN FALSE
           END
$$;

-- -----------------------------------------------------------------------------
-- STAGING (one table per CSV, columns in file order, all TEXT)
-- -----------------------------------------------------------------------------
CREATE TABLE staging.tickets (
    ticket_id text, customer_id text, agent_id text, team_id text,
    created_at text, first_response_at text, resolved_at text,
    priority text, category text, subcategory text, channel text, ticket_status text,
    sla_target_hours text, first_response_time_hours text, resolution_time_hours text,
    escalation_flag text, reopened_count text, first_contact_resolution text,
    customer_satisfaction text, root_cause text, resolution_type text,
    business_impact text, knowledge_base_used text, region text
);

CREATE TABLE staging.customers (
    customer_id text, customer_name text, industry text, company_size text, region text,
    contract_type text, sla_level text, customer_since text, customer_success_manager text
);

CREATE TABLE staging.agents (
    agent_id text, agent_name text, team_id text, experience_level text, shift text,
    location text, employment_type text, start_date text
);

CREATE TABLE staging.support_teams (
    team_id text, team_name text, support_tier text, primary_location text,
    operating_model text, planned_headcount text, team_lead_agent_id text
);

CREATE TABLE staging.sla_targets (
    sla_rule_id text, sla_level text, priority text, response_target_hours text,
    resolution_target_hours text, clock_basis text, effective_from text, effective_to text
);

CREATE TABLE staging.calendar (
    date_key text, date text, year text, quarter text, month text, month_name text,
    year_month text, iso_year text, iso_week text, day_of_month text, day_of_week text,
    day_name text, is_weekend text, is_uk_bank_holiday text, holiday_name text,
    is_working_day text, fiscal_year text, fiscal_quarter text
);

CREATE TABLE staging.incident_categories (
    subcategory_id text, category_id text, category text, subcategory text,
    default_team_id text, complexity_tier text, is_service_request text
);

-- -----------------------------------------------------------------------------
-- CLEAN (typed). PK / FK / UNIQUE / CHECK constraints: see constraints.sql
-- -----------------------------------------------------------------------------
CREATE TABLE clean.extract_metadata (
    extract_name     text        NOT NULL,
    snapshot_at      timestamp   NOT NULL,
    period_start     date        NOT NULL,
    period_end       date        NOT NULL,
    loaded_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE clean.support_teams (
    team_id             text    NOT NULL,
    team_name           text    NOT NULL,
    support_tier        text    NOT NULL,
    primary_location    text    NOT NULL,
    operating_model     text    NOT NULL,
    planned_headcount   integer NOT NULL,
    team_lead_agent_id  text
);

CREATE TABLE clean.agents (
    agent_id          text NOT NULL,
    agent_name        text NOT NULL,
    team_id           text NOT NULL,
    experience_level  text NOT NULL,
    shift             text,                 -- 2 missing in source; kept NULL
    location          text NOT NULL,
    employment_type   text NOT NULL,
    start_date        date NOT NULL
);

CREATE TABLE clean.customers (
    customer_id               text NOT NULL,
    customer_name             text NOT NULL,
    industry                  text NOT NULL,   -- 'Unknown' where missing in source
    company_size              text NOT NULL,
    region                    text NOT NULL,
    contract_type             text NOT NULL,
    sla_level                 text,            -- NULL only for the Unknown placeholder
    customer_since            date,
    customer_success_manager  text,
    is_placeholder            boolean NOT NULL DEFAULT FALSE
);

CREATE TABLE clean.sla_targets (
    sla_rule_id              text    NOT NULL,
    sla_level                text    NOT NULL,
    priority                 text    NOT NULL,
    response_target_hours    numeric(6,2) NOT NULL,
    resolution_target_hours  numeric(6,2) NOT NULL,
    clock_basis              text    NOT NULL,
    effective_from           date    NOT NULL,
    effective_to             date
);

CREATE TABLE clean.calendar (
    date               date     NOT NULL,
    date_key           integer  NOT NULL,
    year               smallint NOT NULL,
    quarter            smallint NOT NULL,
    month              smallint NOT NULL,
    month_name         text     NOT NULL,
    year_month         text     NOT NULL,
    month_start        date     NOT NULL,
    iso_year           smallint NOT NULL,
    iso_week           smallint NOT NULL,
    day_of_month       smallint NOT NULL,
    day_of_week        smallint NOT NULL,   -- 1 = Monday
    day_name           text     NOT NULL,
    is_weekend         boolean  NOT NULL,
    is_uk_bank_holiday boolean  NOT NULL,
    holiday_name       text,
    is_working_day     boolean  NOT NULL,
    fiscal_year        text     NOT NULL,
    fiscal_quarter     smallint NOT NULL
);

CREATE TABLE clean.incident_categories (
    subcategory_id      text    NOT NULL,
    category_id         text    NOT NULL,
    category            text    NOT NULL,
    subcategory         text    NOT NULL,
    default_team_id     text    NOT NULL,
    complexity_tier     text    NOT NULL,
    is_service_request  boolean NOT NULL
);

-- Maps every category label seen in the source to the controlled value (BR-RULE-12)
CREATE TABLE clean.category_label_map (
    raw_label  text NOT NULL,
    category   text NOT NULL,
    match_type text NOT NULL      -- 'exact' | 'normalised' | 'synonym'
);

CREATE TABLE clean.tickets (
    ticket_id                  text        NOT NULL,
    source_row_count           integer     NOT NULL,   -- >1 where exact duplicate rows were collapsed
    customer_id                text        NOT NULL,   -- 'CUST-UNKNOWN' for orphans (BR-RULE-13)
    source_customer_id         text        NOT NULL,
    agent_id                   text,
    team_id                    text        NOT NULL,
    created_at                 timestamp   NOT NULL,
    first_response_at          timestamp,
    resolved_at                timestamp,
    priority                   text        NOT NULL,
    category                   text        NOT NULL,   -- standardised
    category_raw               text        NOT NULL,
    subcategory_id             text,
    subcategory                text,
    channel                    text,
    ticket_status              text        NOT NULL,
    sla_level                  text,
    sla_target_hours           numeric(6,2),
    sla_target_source          text,                   -- 'source' | 'derived' | NULL
    response_target_hours      numeric(6,2),
    first_response_time_hours  numeric(10,2),          -- recomputed from timestamps
    resolution_time_hours      numeric(10,2),          -- recomputed from timestamps
    escalation_flag            boolean     NOT NULL,
    reopened_count             smallint    NOT NULL,
    first_contact_resolution   boolean,
    customer_satisfaction      smallint,               -- valid 1-5 only (BR-RULE-07)
    customer_satisfaction_raw  numeric,
    root_cause                 text,
    resolution_type            text,
    business_impact            text        NOT NULL,
    knowledge_base_used        boolean,
    region                     text        NOT NULL,   -- standardised
    region_raw                 text        NOT NULL,
    -- data-quality flags (row-level facts; KPI eligibility is decided in analytics)
    is_possible_duplicate      boolean     NOT NULL DEFAULT FALSE,
    duplicate_of_ticket_id     text,
    is_invalid_timestamp       boolean     NOT NULL DEFAULT FALSE,
    is_resolution_outlier      boolean     NOT NULL DEFAULT FALSE,
    is_fcr_contradictory       boolean     NOT NULL DEFAULT FALSE,
    is_agent_team_mismatch     boolean     NOT NULL DEFAULT FALSE,
    is_orphan_customer         boolean     NOT NULL DEFAULT FALSE,
    is_priority_impact_mismatch boolean    NOT NULL DEFAULT FALSE,
    is_invalid_csat            boolean     NOT NULL DEFAULT FALSE,
    dq_issue_count             smallint    NOT NULL DEFAULT 0
);

-- -----------------------------------------------------------------------------
-- AUDIT
-- -----------------------------------------------------------------------------
CREATE TABLE audit.load_log (
    log_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    step        text        NOT NULL,
    table_name  text        NOT NULL,
    row_count   bigint      NOT NULL,
    logged_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audit.dq_issues (
    issue_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name  text NOT NULL,
    record_id   text NOT NULL,
    rule_id     text NOT NULL,     -- business rule / check reference
    issue       text NOT NULL,
    action      text NOT NULL,     -- what the pipeline did about it
    detail      text
);
