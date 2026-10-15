import { useEffect, useState } from "react";
import { Search, TriangleAlert } from "lucide-react";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { CustomerAnalysis, CustomerRow } from "../lib/types";
import { fmtInt, fmtNum, fmtPct } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";
import { ErrorState, Skeleton } from "../components/States";

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

function Highlight({ title, rows, value }: {
  title: string;
  rows: { customer_id: string; customer_name: string; sla_level: string }[];
  value: (i: number) => string;
}) {
  return (
    <div className="bg-panel p-4">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {rows.length === 0 ? <p className="mt-2 text-sm text-ink-3">None in this period.</p> : (
        <ol className="mt-2 space-y-1.5 text-sm">
          {rows.map((r, i) => (
            <li key={r.customer_id} className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 truncate text-ink-2" title={`${r.customer_name} (${r.sla_level})`}>{r.customer_name}</span>
              <span className="shrink-0 font-medium tabular-nums text-ink">{value(i)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function CustomersPage() {
  const ready = useFiltersReady();
  const { filters } = useFilters();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<{ key: string; order: "asc" | "desc" }>({ key: "tickets", order: "desc" });
  const [page, setPage] = useState(1);
  const [minTickets, setMinTickets] = useState(1);
  const q = useDebounced(search);
  useEffect(() => setPage(1), [q, minTickets, filters]);

  const c = useApi<CustomerAnalysis>(ready ? "/api/customer-analysis" : null, {
    ...filterParams(filters), search: q, sort: sort.key, order: sort.order, page, page_size: 15, min_tickets: minTickets,
  });
  const d = c.data;
  const h = d?.highlights;

  return (
    <>
      <PageHeader title="Customer intelligence"
        intro="Which customers generate the most work, keep hitting the same problems, or are least satisfied. Customers flagged at risk meet two or more of the warning rules in the last 90 days of data.">
        <FilterBar />
      </PageHeader>

      <div className="space-y-6">
        {c.error && !d ? <ErrorState message={c.error} onRetry={c.reload} /> : !h ? <Skeleton height={170} /> : (
          <section aria-label="Customer highlights"
            className="grid gap-px overflow-hidden rounded-md border border-rule bg-rule sm:grid-cols-2 xl:grid-cols-4">
            <Highlight title="Highest volume" rows={h.top_volume} value={(i) => `${fmtInt(h.top_volume[i].tickets)} tickets`} />
            <Highlight title="Most repeat incidents" rows={h.top_repeat} value={(i) => fmtInt(h.top_repeat[i].repeat_incidents)} />
            <Highlight title="Lowest satisfaction (5+ responses)" rows={h.low_csat} value={(i) => fmtNum(h.low_csat[i].avg_csat)} />
            <Highlight title="Highest breach rate (10+ resolved)" rows={h.high_breach} value={(i) => fmtPct(h.high_breach[i].sla_breach_pct)} />
          </section>
        )}

        <Panel title="All customers" loading={!d && c.loading} error={d ? null : c.error} onRetry={c.reload}
          description={d ? `${fmtInt(d.summary.customers)} customers with tickets in this period, ${fmtInt(d.summary.at_risk_customers)} flagged at risk.` : undefined}
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <label className="relative">
                <span className="sr-only">Search customers</span>
                <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
                <input type="search" value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search name or ID" className="control w-52 pl-8" />
              </label>
              <label className="text-xs text-ink-2">
                <span className="sr-only">Minimum tickets</span>
                <select className="control" value={minTickets} onChange={(e) => setMinTickets(Number(e.target.value))}>
                  <option value={1}>Any volume</option>
                  <option value={10}>10+ tickets</option>
                  <option value={25}>25+ tickets</option>
                  <option value={50}>50+ tickets</option>
                </select>
              </label>
            </div>
          }>
          {d && (
            <div className={c.loading ? "opacity-60 transition-opacity" : ""} aria-busy={c.loading}>
              <DataTable<CustomerRow>
                caption="Customers" rowKey={(r) => r.customer_id} rows={d.items}
                server={{ page: d.page, pageSize: d.page_size, total: d.total, sort: sort.key, order: sort.order,
                  onSort: (key, order) => { setSort({ key, order }); setPage(1); }, onPage: setPage }}
                columns={[
                  { key: "customer_name", header: "Customer", render: (r) => (
                    <span className="flex items-center gap-2">
                      <span className="font-medium">{r.customer_name}</span>
                      {r.is_at_risk && (
                        <span className="inline-flex items-center gap-1 rounded-sm bg-bad/10 px-1.5 py-0.5 text-xs font-medium text-bad">
                          <TriangleAlert size={12} aria-hidden="true" /> At risk
                        </span>
                      )}
                    </span>) },
                  { key: "sla_level", header: "SLA", sortable: false },
                  { key: "industry", header: "Industry", sortable: false },
                  { key: "tickets", header: "Tickets", align: "right", render: (r) => fmtInt(r.tickets) },
                  { key: "repeat_incidents", header: "Repeats", align: "right", render: (r) => fmtInt(r.repeat_incidents) },
                  { key: "sla_breach_pct", header: "Breach rate", align: "right", render: (r) => fmtPct(r.sla_breach_pct) },
                  { key: "avg_csat", header: "CSAT", align: "right",
                    render: (r) => r.csat_responses ? `${fmtNum(r.avg_csat)} (${r.csat_responses})` : "–" },
                  { key: "escalations", header: "Escalations", align: "right", render: (r) => fmtInt(r.escalations) },
                  { key: "open_tickets", header: "Open", align: "right", render: (r) => fmtInt(r.open_tickets) },
                ]} />
              {c.error && <p className="mt-2 text-sm text-bad">{c.error}</p>}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
