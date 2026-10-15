import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { Overview as OverviewData } from "../lib/types";
import { fmtDate, fmtHours, fmtInt, fmtMonth, fmtNum, fmtPct } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { KpiStrip, type KpiItem } from "../components/KpiStrip";
import { Panel } from "../components/Panel";
import { ErrorState, Skeleton } from "../components/States";
import { AXIS, ChartTooltip, GRID, Legend, SERIES } from "../components/charts";
import { DataTable } from "../components/DataTable";

const TARGET_BREACH = 15; // OBJ-01 in docs/01_business_problem.md

function Headline({ data }: { data: OverviewData }) {
  const { filters } = useFilters();
  const c = data.current;
  const ch = data.change.sla_breach_pct;
  const days = data.previous_period
    ? Math.round((Date.parse(filters.end_date) - Date.parse(filters.start_date)) / 86400000) + 1
    : null;
  return (
    <div className="max-w-4xl">
      <p className="text-xl leading-snug text-ink sm:text-3xl sm:leading-tight">
        <span className="figure">{fmtPct(c.sla_breach_pct)}</span> of resolved tickets missed their SLA
        between {fmtDate(filters.start_date)} and {fmtDate(filters.end_date)}
        {ch !== undefined && ch !== null && days ? (
          <>, {Math.abs(ch) < 0.05 ? "level with" : ch > 0 ? `up ${fmtNum(Math.abs(ch), 1)} points on` : `down ${fmtNum(Math.abs(ch), 1)} points on`} the previous {days} days.</>
        ) : "."}
      </p>
      <p className="mt-2 text-ink-2">
        {fmtInt(c.total_tickets)} tickets logged, {fmtInt(c.open_tickets)} still open at the extract date.
        The target is {TARGET_BREACH}% or lower.
      </p>
    </div>
  );
}

export default function Overview() {
  const ready = useFiltersReady();
  const { filters } = useFilters();
  const ov = useApi<OverviewData>(ready ? "/api/overview" : null, filterParams(filters));
  const d = ov.data;
  const c = d?.current;
  const ch = d?.change ?? {};
  const empty = !!d && d.current.total_tickets === 0;

  const kpis: KpiItem[] = c ? [
    { label: "Total tickets", value: fmtInt(c.total_tickets), change: ch.total_tickets, changeDigits: 1, better: "neutral",
      help: "Valid tickets created in the period (possible duplicates removed)." },
    { label: "Open tickets", value: fmtInt(c.open_tickets), better: "down", change: ch.open_tickets,
      help: "Tickets from this period still New, In Progress, Pending Customer or On Hold at the extract date." },
    { label: "SLA compliance", value: fmtPct(c.sla_compliance_pct), change: ch.sla_compliance_pct, changeUnit: " pts", better: "up",
      help: "Share of resolved tickets resolved within their contractual resolution target." },
    { label: "SLA breaches", value: fmtPct(c.sla_breach_pct), change: ch.sla_breach_pct, changeUnit: " pts", better: "down",
      help: "Share of resolved tickets whose resolution time exceeded the SLA target. Target: 15% or lower." },
    { label: "Avg resolution", value: fmtHours(c.avg_resolution_hours), change: ch.avg_resolution_hours, changeUnit: " h", better: "down",
      sub: `median ${fmtHours(c.median_resolution_hours)}`,
      help: "Mean hours from logging to resolution, excluding tickets left open by mistake (> 30 days or > 10x target)." },
    { label: "First-contact resolution", value: fmtPct(c.fcr_pct), change: ch.fcr_pct, changeUnit: " pts", better: "up",
      help: "Resolved at the first interaction with no escalation and no reopen." },
    { label: "Reopen rate", value: fmtPct(c.reopen_pct), change: ch.reopen_pct, changeUnit: " pts", better: "down",
      help: "Resolved tickets that were reopened at least once." },
    { label: "Avg satisfaction", value: c.avg_csat === null ? "–" : `${fmtNum(c.avg_csat)} / 5`, change: ch.avg_csat,
      changeDigits: 2, better: "up", sub: `${fmtInt(c.csat_responses)} responses`,
      help: "Mean post-resolution survey score (1-5). Breached tickets respond more often, so this skews slightly low." },
  ] : [];

  const monthly = d?.monthly ?? [];
  const monthTable = (
    <DataTable caption="Monthly KPIs" rowKey={(r) => r.month} rows={monthly} pageSize={24} dense
      columns={[
        { key: "month", header: "Month", render: (r) => fmtMonth(r.month) },
        { key: "tickets", header: "Tickets", align: "right", render: (r) => fmtInt(r.tickets) },
        { key: "sla_breach_pct", header: "Breach %", align: "right", render: (r) => fmtPct(r.sla_breach_pct) },
        { key: "median_resolution_hours", header: "Median resolution", align: "right", render: (r) => fmtHours(r.median_resolution_hours) },
        { key: "fcr_pct", header: "FCR %", align: "right", render: (r) => fmtPct(r.fcr_pct) },
        { key: "reopen_pct", header: "Reopen %", align: "right", render: (r) => fmtPct(r.reopen_pct) },
        { key: "avg_csat", header: "CSAT", align: "right", render: (r) => fmtNum(r.avg_csat) },
      ]} />
  );

  return (
    <>
      <PageHeader title="Executive overview"
        intro="How the service desk is performing against its SLAs, and how that compares with the previous period of the same length.">
        <FilterBar />
      </PageHeader>

      <div className="space-y-6">
        {ov.error ? <ErrorState message={ov.error} onRetry={ov.reload} />
          : !d || ov.loading ? <div className="space-y-3"><Skeleton height={80} className="max-w-3xl" /><Skeleton height={110} /></div>
            : empty ? <Panel title="No data" empty><span /></Panel>
              : (
                <>
                  <Headline data={d} />
                  <KpiStrip label="Headline KPIs" items={kpis} />
                  {d.previous_period && (
                    <p className="text-xs text-ink-3">
                      Changes compare with {fmtDate(d.previous_period.start_date)} – {fmtDate(d.previous_period.end_date)}.
                    </p>
                  )}
                </>
              )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="SLA breach rate by month" description="Dashed line: the 15% target." loading={ov.loading}
            error={ov.error} onRetry={ov.reload} empty={empty} table={monthTable}>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={monthly} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
                <YAxis {...AXIS} unit="%" domain={[0, "auto"]} />
                <ReferenceLine y={TARGET_BREACH} stroke="#46535c" strokeDasharray="4 4" />
                <Tooltip content={<ChartTooltip formatter={(v) => fmtPct(v)} labelFormatter={fmtMonth} />} />
                <Line type="monotone" dataKey="sla_breach_pct" name="Breach rate" stroke={SERIES[0]} strokeWidth={2}
                  dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Tickets logged per month" loading={ov.loading} error={ov.error} onRetry={ov.reload} empty={empty}
            table={monthTable}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={monthly} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
                <YAxis {...AXIS} />
                <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtInt(v)} labelFormatter={fmtMonth} />} />
                <Bar dataKey="tickets" name="Tickets" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={36} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="First-contact resolution and reopen rate" loading={ov.loading} error={ov.error}
            onRetry={ov.reload} empty={empty} table={monthTable}>
            <Legend items={[{ label: "First-contact resolution", color: SERIES[0] }, { label: "Reopen rate", color: SERIES[1] }]} />
            <ResponsiveContainer width="100%" height={226}>
              <LineChart data={monthly} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
                <YAxis {...AXIS} unit="%" domain={[0, "auto"]} />
                <Tooltip content={<ChartTooltip formatter={(v) => fmtPct(v)} labelFormatter={fmtMonth} />} />
                <Line type="monotone" dataKey="fcr_pct" name="First-contact resolution" stroke={SERIES[0]} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="reopen_pct" name="Reopen rate" stroke={SERIES[1]} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Customer satisfaction by month" description="Average survey score on a 1–5 scale."
            loading={ov.loading} error={ov.error} onRetry={ov.reload} empty={empty} table={monthTable}>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={monthly} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="month" tickFormatter={fmtMonth} {...AXIS} />
                <YAxis {...AXIS} domain={[3, 5]} tickCount={5} />
                <Tooltip content={<ChartTooltip formatter={(v) => fmtNum(v)} labelFormatter={fmtMonth} />} />
                <Line type="monotone" dataKey="avg_csat" name="Average CSAT" stroke={SERIES[0]} strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>
        </div>
      </div>
    </>
  );
}
