import { Bar, BarChart, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { RootCauses } from "../lib/types";
import { fmtHours, fmtInt, fmtPct } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";
import { AXIS, ChartTooltip, GRID, Legend, SERIES } from "../components/charts";

const PRIORITIES = ["P1", "P2", "P3", "P4"] as const;
// sequential blue ramp (light -> dark) for the matrix
const RAMP = ["#eef4fc", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"];

function cellColour(pct: number | null): { bg: string; fg: string } {
  if (pct === null) return { bg: "#f6f7f5", fg: "#6b7780" };
  const i = Math.min(RAMP.length - 1, Math.floor(pct / 10));
  return { bg: RAMP[i], fg: i >= 4 ? "#ffffff" : "#14212b" };
}

function Matrix({ data }: { data: RootCauses }) {
  const causes = data.pareto.map((p) => p.root_cause);
  const lookup = new Map(data.matrix.map((m) => [`${m.root_cause}|${m.priority}`, m]));
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-[2px] text-sm">
        <caption className="sr-only">Incidents and breach rate by root cause and priority</caption>
        <thead>
          <tr className="text-xs text-ink-2">
            <th scope="col" className="px-2 py-1 text-left font-medium">Root cause</th>
            {PRIORITIES.map((p) => <th key={p} scope="col" className="px-2 py-1 font-medium">{p}</th>)}
          </tr>
        </thead>
        <tbody>
          {causes.map((c) => (
            <tr key={c}>
              <th scope="row" className="whitespace-nowrap px-2 py-1 text-left font-normal text-ink">{c}</th>
              {PRIORITIES.map((p) => {
                const m = lookup.get(`${c}|${p}`);
                const { bg, fg } = cellColour(m?.sla_breach_pct ?? null);
                return (
                  <td key={p} className="rounded-sm px-2 py-1.5 text-center tabular-nums" style={{ background: bg, color: fg }}
                    title={m ? `${c}, ${p}: ${fmtInt(m.incidents)} incidents, ${fmtPct(m.sla_breach_pct)} breached` : "No incidents"}>
                    {m ? <><span className="font-medium">{fmtPct(m.sla_breach_pct, 1)}</span>
                      <span className="block text-[11px] opacity-80">{fmtInt(m.incidents)}</span></> : "–"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-ink-3">Cell shows breach rate, with incident count beneath. Darker blue = higher breach rate.</p>
    </div>
  );
}

export default function RootCausesPage() {
  const ready = useFiltersReady();
  const { filters } = useFilters();
  const r = useApi<RootCauses>(ready ? "/api/root-causes" : null, filterParams(filters));
  const d = r.data;
  const state = { loading: r.loading || !d, error: r.error, onRetry: r.reload, empty: !!d && d.pareto.length === 0 };

  return (
    <>
      <PageHeader title="Root cause analysis"
        intro="Which causes generate most incidents and breaches, which problems keep coming back, and what escalation costs. Service requests are excluded.">
        <FilterBar />
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Pareto of incident root causes" className="lg:col-span-2"
          description="Bars: share of incidents. Line: cumulative share. Both use the same percentage scale."
          {...state}
          table={d && (
            <DataTable caption="Root cause Pareto" rowKey={(x) => x.root_cause} rows={d.pareto} dense columns={[
              { key: "root_cause", header: "Root cause" },
              { key: "incidents", header: "Incidents", align: "right", render: (x) => fmtInt(x.incidents) },
              { key: "pct", header: "Share", align: "right", render: (x) => fmtPct(x.pct) },
              { key: "cumulative_pct", header: "Cumulative", align: "right", render: (x) => fmtPct(x.cumulative_pct) },
              { key: "sla_breach_pct", header: "Breach rate", align: "right", render: (x) => fmtPct(x.sla_breach_pct) },
              { key: "median_resolution_hours", header: "Median resolution", align: "right", render: (x) => fmtHours(x.median_resolution_hours) },
            ]} />
          )}>
          <Legend items={[{ label: "Share of incidents", color: SERIES[0] }, { label: "Cumulative share", color: SERIES[1] },
            { label: "80% line", color: "#46535c", dashed: true }]} />
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={d?.pareto ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 40 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="root_cause" {...AXIS} interval={0} angle={-30} textAnchor="end" height={60} />
              <YAxis {...AXIS} unit="%" domain={[0, 100]} />
              <ReferenceLine y={80} stroke="#46535c" strokeDasharray="4 4" />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="pct" name="Share of incidents" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={48} />
              <Line dataKey="cumulative_pct" name="Cumulative share" stroke={SERIES[1]} strokeWidth={2} dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Breach rate by root cause" description="How often incidents with each cause miss their SLA."
          {...state}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={[...(d?.pareto ?? [])].sort((a, b) => (b.sla_breach_pct ?? 0) - (a.sla_breach_pct ?? 0))}
              layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid {...GRID} horizontal={false} vertical />
              <XAxis type="number" {...AXIS} unit="%" />
              <YAxis type="category" dataKey="root_cause" width={160} {...AXIS} />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtPct(v)} />} />
              <Bar dataKey="sla_breach_pct" name="Breach rate" fill={SERIES[0]} radius={[0, 4, 4, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Root cause and priority" description="Breach rate for each combination." {...state}>
          {d && <Matrix data={d} />}
        </Panel>

        <Panel title="Repeat incidents"
          description="Same customer, same subcategory, within 30 days of a previous incident." {...state}>
          {d && (
            <>
              <p className="mb-3 text-ink-2">
                <span className="figure text-2xl text-ink">{fmtPct(d.repeat_summary.repeat_incident_pct)}</span>{" "}
                of incidents were repeats ({fmtInt(d.repeat_summary.repeat_incidents)} of {fmtInt(d.repeat_summary.eligible_incidents)}).
              </p>
              <DataTable caption="Customers with the most repeat incidents" rowKey={(x) => `${x.customer_id}|${x.subcategory}`}
                rows={d.repeat_top} dense columns={[
                  { key: "customer_name", header: "Customer" },
                  { key: "subcategory", header: "Issue" },
                  { key: "repeat_incidents", header: "Repeats", align: "right", render: (x) => fmtInt(x.repeat_incidents) },
                  { key: "main_root_cause", header: "Main root cause", render: (x) => x.main_root_cause ?? "–" },
                ]} />
            </>
          )}
        </Panel>

        <Panel title="Escalation analysis" description="Median resolution time for escalated and non-escalated tickets."
          {...state}
          table={d && (
            <DataTable caption="Escalation by priority" rowKey={(x) => x.priority} rows={d.escalation} dense columns={[
              { key: "priority", header: "Priority" },
              { key: "escalation_pct", header: "Escalated", align: "right", render: (x) => fmtPct(x.escalation_pct) },
              { key: "median_hours_not_escalated", header: "Median (not)", align: "right", render: (x) => fmtHours(x.median_hours_not_escalated) },
              { key: "median_hours_escalated", header: "Median (escalated)", align: "right", render: (x) => fmtHours(x.median_hours_escalated) },
              { key: "breach_pct_not_escalated", header: "Breach (not)", align: "right", render: (x) => fmtPct(x.breach_pct_not_escalated) },
              { key: "breach_pct_escalated", header: "Breach (escalated)", align: "right", render: (x) => fmtPct(x.breach_pct_escalated) },
            ]} />
          )}>
          <Legend items={[{ label: "Not escalated", color: SERIES[0] }, { label: "Escalated", color: SERIES[1] }]} />
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={d?.escalation ?? []} margin={{ top: 8, right: 12, left: -8, bottom: 0 }} barGap={2}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="priority" {...AXIS} />
              <YAxis {...AXIS} unit=" h" />
              <Tooltip cursor={{ fill: "#eef1ef" }} content={<ChartTooltip formatter={(v) => fmtHours(v)} />} />
              <Bar dataKey="median_hours_not_escalated" name="Not escalated" fill={SERIES[0]} radius={[4, 4, 0, 0]} maxBarSize={32} />
              <Bar dataKey="median_hours_escalated" name="Escalated" fill={SERIES[1]} radius={[4, 4, 0, 0]} maxBarSize={32} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Subcategories with the longest resolution times"
          description="Ranked by 90th-percentile resolution time (subcategories with at least 20 tickets)." {...state}>
          {d && (
            <DataTable caption="Slowest subcategories" rowKey={(x) => x.subcategory} rows={d.long_categories} dense columns={[
              { key: "subcategory", header: "Subcategory" },
              { key: "category", header: "Category" },
              { key: "median_hours", header: "Median", align: "right", render: (x) => fmtHours(x.median_hours) },
              { key: "p90_hours", header: "90th pct", align: "right", render: (x) => fmtHours(x.p90_hours) },
              { key: "sla_breach_pct", header: "Breach rate", align: "right", render: (x) => fmtPct(x.sla_breach_pct) },
            ]} />
          )}
        </Panel>
      </div>
    </>
  );
}
