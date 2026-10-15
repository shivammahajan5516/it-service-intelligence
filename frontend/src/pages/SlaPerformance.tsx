import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { SlaPerformance } from "../lib/types";
import { fmtHours, fmtInt, fmtMonth, fmtNum, fmtPct } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";
import { AXIS, ChartTooltip, GRID, Legend, PRIORITY_COLOR, SERIES } from "../components/charts";

const PRIORITIES = ["P1", "P2", "P3", "P4"] as const;
const TOP_RADIUS: [number, number, number, number] = [4, 4, 0, 0];
const NO_RADIUS: [number, number, number, number] = [0, 0, 0, 0];

export default function SlaPerformancePage() {
  const ready = useFiltersReady();
  const { filters } = useFilters();
  const s = useApi<SlaPerformance>(ready ? "/api/sla-performance" : null, filterParams(filters));
  const d = s.data;
  const state = { loading: s.loading || !d, error: s.error, onRetry: s.reload,
    empty: !!d && d.by_priority.length === 0 };
  const priorityLegend = PRIORITIES.map((p) => ({ label: p, color: PRIORITY_COLOR[p] }));

  return (
    <>
      <PageHeader title="SLA performance"
        intro="Where resolution targets are being missed: by priority, category, team and channel, and how that has moved over time.">
        <FilterBar show={["date", "priority", "team", "region"]} />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Compliance by priority" description="Share resolved within target; P1 targets are the tightest."
          {...state}
          table={d && (
            <DataTable caption="SLA by priority" rowKey={(r) => r.priority} rows={d.by_priority} dense columns={[
              { key: "priority", header: "Priority" },
              { key: "sla_population", header: "Resolved", align: "right", render: (r) => fmtInt(r.sla_population) },
              { key: "sla_compliance_pct", header: "Compliance", align: "right", render: (r) => fmtPct(r.sla_compliance_pct) },
              { key: "response_met_pct", header: "Response met", align: "right", render: (r) => fmtPct(r.response_met_pct) },
              { key: "median_resolution_hours", header: "Median", align: "right", render: (r) => fmtHours(r.median_resolution_hours) },
              { key: "p90_resolution_hours", header: "90th pct", align: "right", render: (r) => fmtHours(r.p90_resolution_hours) },
            ]} />
          )}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={d?.by_priority ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="priority" {...AXIS} />
              <YAxis {...AXIS} unit="%" domain={[0, 100]} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="sla_compliance_pct" name="SLA compliance" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={56} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Breaches by category" description="Number of SLA breaches; hover for the breach rate."
          {...state}
          table={d && (
            <DataTable caption="Breaches by category" rowKey={(r) => r.category} rows={d.by_category} dense columns={[
              { key: "category", header: "Category" },
              { key: "breaches", header: "Breaches", align: "right", render: (r) => fmtInt(r.breaches) },
              { key: "sla_population", header: "Resolved", align: "right", render: (r) => fmtInt(r.sla_population) },
              { key: "sla_breach_pct", header: "Breach rate", align: "right", render: (r) => fmtPct(r.sla_breach_pct) },
            ]} />
          )}>
          <ResponsiveContainer width="100%" height={290}>
            <BarChart data={d?.by_category ?? []} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid {...GRID} horizontal={false} vertical />
              <XAxis type="number" {...AXIS} />
              <YAxis type="category" dataKey="category" width={150} {...AXIS} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtInt(v)} />} />
              <Bar dataKey="breaches" name="Breaches" fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="SLA compliance by team" {...state}
          table={d && (
            <DataTable caption="SLA by team" rowKey={(r) => r.team_id} rows={d.by_team} dense columns={[
              { key: "team_name", header: "Team" },
              { key: "sla_population", header: "Resolved", align: "right", render: (r) => fmtInt(r.sla_population) },
              { key: "breaches", header: "Breaches", align: "right", render: (r) => fmtInt(r.breaches) },
              { key: "sla_compliance_pct", header: "Compliance", align: "right", render: (r) => fmtPct(r.sla_compliance_pct) },
            ]} />
          )}>
          <ResponsiveContainer width="100%" height={290}>
            <BarChart data={d?.by_team ?? []} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid {...GRID} horizontal={false} vertical />
              <XAxis type="number" {...AXIS} unit="%" domain={[0, 100]} />
              <YAxis type="category" dataKey="team_name" width={170} {...AXIS} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="sla_compliance_pct" name="SLA compliance" fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Resolution-time distribution" description="Resolved tickets by how long they took, stacked by priority."
          {...state}
          table={d && (
            <DataTable caption="Resolution time distribution" rowKey={(r) => r.bucket} rows={d.resolution_distribution} dense
              columns={[{ key: "bucket", header: "Resolution time", sortable: false },
                ...PRIORITIES.map((p) => ({ key: p, header: p, align: "right" as const, render: (r: SlaPerformance["resolution_distribution"][number]) => fmtInt(r[p]) }))]} />
          )}>
          <Legend items={priorityLegend} />
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={d?.resolution_distribution ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="bucket" {...AXIS} />
              <YAxis {...AXIS} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtInt(v)} />} />
              {PRIORITIES.map((p, i) => (
                <Bar key={p} dataKey={p} name={p} stackId="a" fill={PRIORITY_COLOR[p]} stroke="#ffffff" strokeWidth={1}
                  maxBarSize={56} radius={i === PRIORITIES.length - 1 ? TOP_RADIUS : NO_RADIUS} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="First response by channel" description="Share of tickets acknowledged within the response target."
          {...state}
          table={d && (
            <DataTable caption="First response by channel" rowKey={(r) => r.channel} rows={d.first_response} dense columns={[
              { key: "channel", header: "Channel" },
              { key: "tickets", header: "Tickets", align: "right", render: (r) => fmtInt(r.tickets) },
              { key: "response_met_pct", header: "Within target", align: "right", render: (r) => fmtPct(r.response_met_pct) },
              { key: "median_response_minutes", header: "Median response", align: "right",
                render: (r) => r.median_response_minutes === null ? "–" : `${fmtNum(r.median_response_minutes, 1)} min` },
            ]} />
          )}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={d?.first_response ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="channel" {...AXIS} />
              <YAxis {...AXIS} unit="%" domain={[0, 100]} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="response_met_pct" name="Response within target" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={56} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Breach rate trend by priority" {...state}
          table={d && (
            <DataTable caption="Breach trend by priority" rowKey={(r) => r.month} rows={d.breach_trend} pageSize={24} dense
              columns={[{ key: "month", header: "Month", render: (r) => fmtMonth(r.month) },
                ...PRIORITIES.map((p) => ({ key: p, header: p, align: "right" as const,
                  render: (r: SlaPerformance["breach_trend"][number]) => fmtPct(r[p] ?? null) }))]} />
          )}>
          <Legend items={priorityLegend} />
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={d?.breach_trend ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
              <YAxis {...AXIS} unit="%" domain={[0, "auto"]} />
              <Tooltip content={<ChartTooltip formatter={(v) => fmtPct(v)} labelFormatter={fmtMonth} />} />
              {PRIORITIES.map((p) => (
                <Line key={p} type="monotone" dataKey={p} name={p} stroke={PRIORITY_COLOR[p]} strokeWidth={2} dot={false} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Breach rate by region" className="lg:col-span-2"
          description="Regional differences largely reflect the mix of contract levels, not region itself (see SQL query Q37)."
          {...state}>
          {d && (
            <DataTable caption="Breach rate by region" rowKey={(r) => r.region} rows={d.by_region} dense
              initialSort={{ key: "sla_breach_pct", order: "desc" }} columns={[
                { key: "region", header: "Region" },
                { key: "sla_population", header: "Resolved", align: "right", render: (r) => fmtInt(r.sla_population) },
                { key: "sla_breach_pct", header: "Breach rate", align: "right", render: (r) => fmtPct(r.sla_breach_pct) },
              ]} />
          )}
        </Panel>
      </div>
    </>
  );
}
