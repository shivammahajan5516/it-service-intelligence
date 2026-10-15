import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { TeamPerformance, TeamRow } from "../lib/types";
import { fmtHours, fmtInt, fmtMonth, fmtNum, fmtPct } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";
import { AXIS, ChartTooltip, GRID, Legend, SERIES } from "../components/charts";

type MetricKey = "tickets_per_agent_month" | "tickets" | "median_resolution_hours" | "sla_compliance_pct"
  | "avg_csat" | "reopen_pct" | "fcr_pct";

const METRICS: { key: MetricKey; label: string; fmt: (v: number) => string; better: "higher" | "lower" | "neutral" }[] = [
  { key: "tickets_per_agent_month", label: "Tickets per agent per month", fmt: (v) => fmtNum(v, 1), better: "neutral" },
  { key: "tickets", label: "Ticket workload", fmt: fmtInt, better: "neutral" },
  { key: "median_resolution_hours", label: "Median resolution time", fmt: fmtHours, better: "lower" },
  { key: "sla_compliance_pct", label: "SLA compliance", fmt: (v) => fmtPct(v), better: "higher" },
  { key: "avg_csat", label: "Average satisfaction", fmt: (v) => fmtNum(v), better: "higher" },
  { key: "reopen_pct", label: "Reopen rate", fmt: (v) => fmtPct(v), better: "lower" },
  { key: "fcr_pct", label: "First-contact resolution", fmt: (v) => fmtPct(v), better: "higher" },
];

export default function TeamPerformancePage() {
  const ready = useFiltersReady();
  const { filters, meta } = useFilters();
  const t = useApi<TeamPerformance>(ready ? "/api/team-performance" : null, filterParams(filters));
  const [metric, setMetric] = useState<MetricKey>("tickets_per_agent_month");
  const d = t.data;
  const m = METRICS.find((x) => x.key === metric) ?? METRICS[0];
  const state = { loading: t.loading || !d, error: t.error, onRetry: t.reload, empty: !!d && d.teams.every((x) => x.tickets === 0) };
  const chartRows = [...(d?.teams ?? [])].sort((a, b) => (Number(b[metric] ?? 0) - Number(a[metric] ?? 0)));
  const teamIds = (d?.teams ?? []).map((x) => x.team_id);
  const teamName = (id: string) => meta?.teams.find((x) => x.team_id === id)?.team_name ?? id;

  return (
    <>
      <PageHeader title="Team performance"
        intro="A like-for-like scorecard for the eight resolver teams. Teams handle different work, so compare breach rates alongside the priority mix on the SLA page.">
        <FilterBar show={["date", "priority", "team", "category", "region"]} />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Team comparison" className="lg:col-span-2" {...state}>
          {d && (
            <DataTable caption="Team scorecard" rowKey={(r) => r.team_id} rows={d.teams} pageSize={10}
              initialSort={{ key: "sla_compliance_pct", order: "asc" }}
              columns={[
                { key: "team_name", header: "Team", render: (r: TeamRow) => <span className="font-medium">{r.team_name}</span> },
                { key: "tickets", header: "Tickets", align: "right", render: (r) => fmtInt(r.tickets) },
                { key: "tickets_per_agent_month", header: "Per agent / month", align: "right", render: (r) => fmtNum(r.tickets_per_agent_month, 1),
                  help: "Tickets divided by planned headcount and months in range" },
                { key: "median_resolution_hours", header: "Median resolution", align: "right", render: (r) => fmtHours(r.median_resolution_hours) },
                { key: "sla_compliance_pct", header: "SLA compliance", align: "right", render: (r) => fmtPct(r.sla_compliance_pct) },
                { key: "avg_csat", header: "CSAT", align: "right", render: (r) => fmtNum(r.avg_csat) },
                { key: "reopen_pct", header: "Reopen", align: "right", render: (r) => fmtPct(r.reopen_pct) },
                { key: "fcr_pct", header: "FCR", align: "right", render: (r) => fmtPct(r.fcr_pct) },
                { key: "escalation_pct", header: "Escalated", align: "right", render: (r) => fmtPct(r.escalation_pct) },
                { key: "open_tickets", header: "Open", align: "right", render: (r) => fmtInt(r.open_tickets) },
              ]} />
          )}
        </Panel>

        <Panel title={`Compare teams: ${m.label.toLowerCase()}`}
          description={m.better === "neutral" ? "Higher means more work per person." : m.better === "higher" ? "Higher is better." : "Lower is better."}
          {...state}
          actions={
            <label className="text-xs text-ink-2">
              <span className="sr-only">Metric</span>
              <select className="control" value={metric} onChange={(e) => setMetric(e.target.value as MetricKey)}>
                {METRICS.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
              </select>
            </label>
          }>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartRows} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid {...GRID} horizontal={false} vertical />
              <XAxis type="number" {...AXIS} />
              <YAxis type="category" dataKey="team_name" width={170} {...AXIS} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={m.fmt} />} />
              <Bar dataKey={metric} name={m.label} fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Monthly ticket workload by team" {...state}>
          <Legend items={teamIds.map((id, i) => ({ label: teamName(id), color: SERIES[i % SERIES.length] }))} />
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={d?.monthly_workload ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
              <YAxis {...AXIS} />
              <Tooltip content={<ChartTooltip formatter={fmtInt} labelFormatter={fmtMonth} />} />
              {teamIds.map((id, i) => (
                <Line key={id} type="monotone" dataKey={id} name={teamName(id)} stroke={SERIES[i % SERIES.length]}
                  strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Panel>
      </div>
    </>
  );
}
