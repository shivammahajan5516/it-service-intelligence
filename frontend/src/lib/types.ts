// Response types mirroring backend/app/services.py

export type Priority = "P1" | "P2" | "P3" | "P4";

export interface FilterState {
  start_date: string;
  end_date: string;
  priority: string[];
  team: string[];
  category: string[];
  region: string[];
}

export interface Meta {
  teams: { team_id: string; team_name: string; support_tier: string; planned_headcount: number }[];
  priorities: Priority[];
  categories: string[];
  regions: string[];
  min_date: string;
  max_date: string;
  snapshot_at: string;
  synthetic_data: boolean;
}

export interface Kpis {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  sla_population: number;
  sla_compliance_pct: number | null;
  sla_breach_pct: number | null;
  avg_resolution_hours: number | null;
  median_resolution_hours: number | null;
  fcr_pct: number | null;
  reopen_pct: number | null;
  escalation_pct: number | null;
  avg_csat: number | null;
  csat_responses: number;
  repeat_incident_pct: number | null;
}

export interface MonthRow {
  month: string;
  tickets: number;
  resolved: number;
  sla_breach_pct: number | null;
  sla_compliance_pct: number | null;
  median_resolution_hours: number | null;
  fcr_pct: number | null;
  reopen_pct: number | null;
  escalation_pct: number | null;
  avg_csat: number | null;
  csat_responses: number;
}

export interface Overview {
  current: Kpis;
  previous: Kpis | null;
  change: Partial<Record<keyof Kpis, number>>;
  previous_period: { start_date: string; end_date: string } | null;
  monthly: MonthRow[];
}

export interface SlaPerformance {
  by_priority: {
    priority: Priority; tickets: number; sla_population: number; sla_compliance_pct: number | null;
    sla_breach_pct: number | null; response_met_pct: number | null; median_resolution_hours: number | null;
    p90_resolution_hours: number | null;
  }[];
  by_category: { category: string; sla_population: number; breaches: number; sla_breach_pct: number | null }[];
  by_team: { team_id: string; team_name: string; sla_population: number; breaches: number;
    sla_compliance_pct: number | null; sla_breach_pct: number | null }[];
  by_region: { region: string; sla_population: number; sla_breach_pct: number | null }[];
  resolution_distribution: { bucket: string; sort_order: number; P1: number; P2: number; P3: number; P4: number }[];
  first_response: { channel: string; tickets: number; response_met_pct: number | null; median_response_minutes: number | null }[];
  breach_trend: { month: string; P1?: number | null; P2?: number | null; P3?: number | null; P4?: number | null }[];
}

export interface RootCauses {
  pareto: { root_cause: string; incidents: number; sla_breach_pct: number | null; median_resolution_hours: number | null;
    pct: number; cumulative_pct: number }[];
  matrix: { root_cause: string; priority: Priority; incidents: number; sla_breach_pct: number | null }[];
  repeat_summary: { repeat_incidents: number; eligible_incidents: number; repeat_incident_pct: number | null };
  repeat_top: { customer_id: string; customer_name: string; subcategory: string; incidents: number;
    repeat_incidents: number; main_root_cause: string | null }[];
  escalation: { priority: Priority; escalation_pct: number | null; median_hours_escalated: number | null;
    median_hours_not_escalated: number | null; breach_pct_escalated: number | null; breach_pct_not_escalated: number | null }[];
  long_categories: { category: string; subcategory: string; tickets: number; median_hours: number | null;
    p90_hours: number | null; sla_breach_pct: number | null }[];
}

export interface TeamRow {
  team_id: string; team_name: string; support_tier: string; planned_headcount: number; tickets: number;
  tickets_per_agent_month: number | null; median_resolution_hours: number | null; avg_resolution_hours: number | null;
  sla_compliance_pct: number | null; sla_breach_pct: number | null; avg_csat: number | null; csat_responses: number;
  reopen_pct: number | null; fcr_pct: number | null; escalation_pct: number | null; open_tickets: number;
}

export interface TeamPerformance {
  teams: TeamRow[];
  monthly_workload: ({ month: string } & Record<string, number | string>)[];
}

export interface CustomerRow {
  customer_id: string; customer_name: string; industry: string; company_size: string; sla_level: string;
  hq_region: string; customer_success_manager: string | null; tickets: number; resolved_tickets: number;
  repeat_incidents: number; repeat_incident_pct: number | null; breaches: number; sla_breach_pct: number | null;
  avg_csat: number | null; csat_responses: number; escalations: number; open_tickets: number; is_at_risk: boolean;
}

export interface CustomerAnalysis {
  summary: { customers: number; at_risk_customers: number; tickets: number };
  items: CustomerRow[];
  total: number;
  page: number;
  page_size: number;
  sort: string;
  order: "asc" | "desc";
  highlights: {
    top_volume: { customer_id: string; customer_name: string; sla_level: string; tickets: number; sla_breach_pct: number | null }[];
    top_repeat: { customer_id: string; customer_name: string; sla_level: string; repeat_incidents: number; repeat_incident_pct: number | null }[];
    low_csat: { customer_id: string; customer_name: string; sla_level: string; avg_csat: number | null; csat_responses: number }[];
    high_breach: { customer_id: string; customer_name: string; sla_level: string; sla_breach_pct: number | null; resolved_tickets: number }[];
  };
}

export interface TicketRow {
  ticket_id: string; created_at: string; priority: Priority; category: string; subcategory: string | null;
  team_id: string; team_name: string; customer_id: string; customer_name: string; channel: string | null;
  ticket_status: string; sla_target_hours: number | null; resolution_time_hours: number | null;
  sla_breached: boolean | null; escalation_flag: boolean; reopened_count: number;
  customer_satisfaction: number | null; root_cause: string | null;
}

export interface Tickets {
  items: TicketRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface DataQuality {
  rules: { rule_id: string; issue: string; action: string; records: number }[];
  total_issues: number;
}
