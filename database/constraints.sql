-- =============================================================================
-- constraints.sql  -  keys and integrity rules on the clean layer
--
-- Applied AFTER transform_clean.sql: a bulk load into unconstrained tables is
-- faster, and if the transform ever produces bad data this file fails loudly
-- with the name of the violated rule instead of a half-loaded table.
-- =============================================================================
\set ON_ERROR_STOP on
BEGIN;

-- ---------------- Primary keys ----------------
ALTER TABLE clean.support_teams       ADD CONSTRAINT pk_support_teams       PRIMARY KEY (team_id);
ALTER TABLE clean.agents              ADD CONSTRAINT pk_agents              PRIMARY KEY (agent_id);
ALTER TABLE clean.customers           ADD CONSTRAINT pk_customers           PRIMARY KEY (customer_id);
ALTER TABLE clean.sla_targets         ADD CONSTRAINT pk_sla_targets         PRIMARY KEY (sla_rule_id);
ALTER TABLE clean.calendar            ADD CONSTRAINT pk_calendar            PRIMARY KEY (date);
ALTER TABLE clean.incident_categories ADD CONSTRAINT pk_incident_categories PRIMARY KEY (subcategory_id);
ALTER TABLE clean.category_label_map  ADD CONSTRAINT pk_category_label_map  PRIMARY KEY (raw_label);
ALTER TABLE clean.tickets             ADD CONSTRAINT pk_tickets             PRIMARY KEY (ticket_id);

-- ---------------- Unique (natural / alternate keys) ----------------
ALTER TABLE clean.support_teams       ADD CONSTRAINT uq_team_name         UNIQUE (team_name);
ALTER TABLE clean.customers           ADD CONSTRAINT uq_customer_name     UNIQUE (customer_name);
ALTER TABLE clean.calendar            ADD CONSTRAINT uq_calendar_date_key UNIQUE (date_key);
ALTER TABLE clean.incident_categories ADD CONSTRAINT uq_subcategory       UNIQUE (subcategory);
ALTER TABLE clean.sla_targets         ADD CONSTRAINT uq_sla_rule          UNIQUE (sla_level, priority, effective_from);

-- ---------------- Foreign keys ----------------
ALTER TABLE clean.agents ADD CONSTRAINT fk_agents_team
    FOREIGN KEY (team_id) REFERENCES clean.support_teams (team_id);
ALTER TABLE clean.support_teams ADD CONSTRAINT fk_team_lead
    FOREIGN KEY (team_lead_agent_id) REFERENCES clean.agents (agent_id);
ALTER TABLE clean.incident_categories ADD CONSTRAINT fk_category_team
    FOREIGN KEY (default_team_id) REFERENCES clean.support_teams (team_id);

ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_customer
    FOREIGN KEY (customer_id)    REFERENCES clean.customers (customer_id);
ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_agent
    FOREIGN KEY (agent_id)       REFERENCES clean.agents (agent_id);
ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_team
    FOREIGN KEY (team_id)        REFERENCES clean.support_teams (team_id);
ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_subcategory
    FOREIGN KEY (subcategory_id) REFERENCES clean.incident_categories (subcategory_id);
ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_duplicate_of
    FOREIGN KEY (duplicate_of_ticket_id) REFERENCES clean.tickets (ticket_id);
-- created date must exist in the calendar (date dimension completeness)
ALTER TABLE clean.tickets ADD COLUMN created_date date GENERATED ALWAYS AS (created_at::date) STORED;
ALTER TABLE clean.tickets ADD CONSTRAINT fk_tickets_created_date
    FOREIGN KEY (created_date) REFERENCES clean.calendar (date);

-- ---------------- CHECK constraints: controlled vocabularies ----------------
ALTER TABLE clean.tickets ADD CONSTRAINT ck_priority
    CHECK (priority IN ('P1', 'P2', 'P3', 'P4'));
ALTER TABLE clean.tickets ADD CONSTRAINT ck_status
    CHECK (ticket_status IN ('New', 'In Progress', 'Pending Customer', 'On Hold',
                             'Resolved', 'Closed', 'Cancelled'));
ALTER TABLE clean.tickets ADD CONSTRAINT ck_channel
    CHECK (channel IS NULL OR channel IN ('Portal', 'Email', 'Phone', 'Chat', 'Monitoring Alert'));
ALTER TABLE clean.tickets ADD CONSTRAINT ck_business_impact
    CHECK (business_impact IN ('Critical', 'High', 'Medium', 'Low'));
ALTER TABLE clean.sla_targets ADD CONSTRAINT ck_sla_priority
    CHECK (priority IN ('P1', 'P2', 'P3', 'P4'));
ALTER TABLE clean.sla_targets ADD CONSTRAINT ck_sla_level
    CHECK (sla_level IN ('Platinum', 'Gold', 'Silver', 'Bronze'));
ALTER TABLE clean.customers ADD CONSTRAINT ck_customer_sla_level
    CHECK (sla_level IN ('Platinum', 'Gold', 'Silver', 'Bronze') OR is_placeholder);
ALTER TABLE clean.customers ADD CONSTRAINT ck_company_size
    CHECK (company_size IN ('SME', 'Mid-Market', 'Enterprise', 'Large Enterprise') OR is_placeholder);
ALTER TABLE clean.agents ADD CONSTRAINT ck_experience
    CHECK (experience_level IN ('Junior', 'Intermediate', 'Senior', 'Lead'));
ALTER TABLE clean.agents ADD CONSTRAINT ck_shift
    CHECK (shift IS NULL OR shift IN ('Early', 'Day', 'Late', 'Night'));
ALTER TABLE clean.agents ADD CONSTRAINT ck_employment
    CHECK (employment_type IN ('Permanent', 'Contractor', 'Outsourced Partner'));
ALTER TABLE clean.incident_categories ADD CONSTRAINT ck_complexity
    CHECK (complexity_tier IN ('Low', 'Medium', 'High'));

-- ---------------- CHECK constraints: ranges and consistency ----------------
ALTER TABLE clean.tickets ADD CONSTRAINT ck_csat_range
    CHECK (customer_satisfaction BETWEEN 1 AND 5);
ALTER TABLE clean.tickets ADD CONSTRAINT ck_reopened_nonneg
    CHECK (reopened_count >= 0);
ALTER TABLE clean.tickets ADD CONSTRAINT ck_sla_target_positive
    CHECK (sla_target_hours > 0);
ALTER TABLE clean.tickets ADD CONSTRAINT ck_source_row_count
    CHECK (source_row_count >= 1);
-- A duration may be negative ONLY if the row is flagged (BR-RULE-06)
ALTER TABLE clean.tickets ADD CONSTRAINT ck_negative_duration_flagged
    CHECK (is_invalid_timestamp OR (COALESCE(resolution_time_hours, 0) >= 0
                                    AND COALESCE(first_response_time_hours, 0) >= 0));
-- Open tickets have no resolution timestamp
ALTER TABLE clean.tickets ADD CONSTRAINT ck_open_not_resolved
    CHECK (ticket_status NOT IN ('New', 'In Progress', 'Pending Customer', 'On Hold')
           OR resolved_at IS NULL);
-- A ticket cannot be a duplicate of itself
ALTER TABLE clean.tickets ADD CONSTRAINT ck_not_self_duplicate
    CHECK (duplicate_of_ticket_id IS DISTINCT FROM ticket_id);
ALTER TABLE clean.support_teams ADD CONSTRAINT ck_headcount
    CHECK (planned_headcount > 0);
ALTER TABLE clean.sla_targets ADD CONSTRAINT ck_sla_targets_order
    CHECK (response_target_hours > 0 AND response_target_hours <= resolution_target_hours);
ALTER TABLE clean.calendar ADD CONSTRAINT ck_day_of_week
    CHECK (day_of_week BETWEEN 1 AND 7);

COMMIT;
