-- =============================================================================
-- indexes.sql  -  indexes chosen for the dashboard / API access paths
--
-- Primary keys and UNIQUE constraints already create indexes. These cover the
-- filter columns the API exposes (date range, priority, team, category,
-- region) and the join / window keys used by the analytics views.
-- =============================================================================
\set ON_ERROR_STOP on

-- Date-range filtering is on every endpoint
CREATE INDEX ix_tickets_created_at   ON clean.tickets (created_at);
-- Composite for "team over a period" - the most common dashboard filter
CREATE INDEX ix_tickets_team_created ON clean.tickets (team_id, created_at);
CREATE INDEX ix_tickets_priority     ON clean.tickets (priority);
CREATE INDEX ix_tickets_category     ON clean.tickets (category);
CREATE INDEX ix_tickets_region       ON clean.tickets (region);
-- FK columns (PostgreSQL does not index FKs automatically)
CREATE INDEX ix_tickets_customer     ON clean.tickets (customer_id);
CREATE INDEX ix_tickets_agent        ON clean.tickets (agent_id);
CREATE INDEX ix_tickets_subcategory  ON clean.tickets (subcategory_id);
-- Repeat-incident window: PARTITION BY customer, subcategory ORDER BY created_at
CREATE INDEX ix_tickets_repeat       ON clean.tickets (customer_id, subcategory_id, created_at);
-- Backlog queries only touch open tickets: a small partial index
CREATE INDEX ix_tickets_open         ON clean.tickets (team_id, priority)
    WHERE ticket_status IN ('New', 'In Progress', 'Pending Customer', 'On Hold');
-- Investigation lists filter on flagged rows only
CREATE INDEX ix_tickets_dq           ON clean.tickets (dq_issue_count) WHERE dq_issue_count > 0;

CREATE INDEX ix_agents_team          ON clean.agents (team_id);
CREATE INDEX ix_dq_issues_record     ON audit.dq_issues (record_id);
CREATE INDEX ix_dq_issues_rule       ON audit.dq_issues (rule_id);

ANALYZE clean.tickets;
ANALYZE clean.customers;
ANALYZE clean.agents;
