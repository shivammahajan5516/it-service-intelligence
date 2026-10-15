import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { useFilters, useFiltersReady } from "../context/FiltersContext";
import { filterParams } from "../lib/api";
import { useApi } from "../lib/useApi";
import type { TicketRow, Tickets } from "../lib/types";
import { fmtDate, fmtHours, fmtInt } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { FilterBar } from "../components/FilterBar";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";

const STATUS = [
  { id: "", label: "All" }, { id: "open", label: "Open" }, { id: "breached", label: "Breached" },
  { id: "resolved", label: "Resolved" }, { id: "cancelled", label: "Cancelled" },
];

function Outcome({ t }: { t: TicketRow }) {
  if (t.sla_breached === null) return <span className="text-ink-3">–</span>;
  return t.sla_breached
    ? <span className="font-medium text-bad">Breached</span>
    : <span className="text-good">Met</span>;
}

export default function TicketsPage() {
  const ready = useFiltersReady();
  const { filters } = useFilters();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ key: string; order: "asc" | "desc" }>({ key: "created_at", order: "desc" });
  const [page, setPage] = useState(1);
  useEffect(() => {
    const id = setTimeout(() => setQ(search), 300);
    return () => clearTimeout(id);
  }, [search]);
  useEffect(() => setPage(1), [q, status, filters]);

  const t = useApi<Tickets>(ready ? "/api/tickets" : null, {
    ...filterParams(filters), status: status || undefined, search: q, sort: sort.key, order: sort.order, page, page_size: 25,
  });
  const d = t.data;

  return (
    <>
      <PageHeader title="Tickets" intro="Every ticket behind the numbers, for drill-down and spot checks.">
        <FilterBar />
      </PageHeader>
      <Panel title={d ? `${fmtInt(d.total)} tickets` : "Tickets"} loading={!d && t.loading} error={d ? null : t.error}
        onRetry={t.reload}
        actions={
          <label className="relative">
            <span className="sr-only">Search tickets</span>
            <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Ticket ID or customer" className="control w-56 pl-8" />
          </label>
        }>
        <div role="tablist" aria-label="Ticket status" className="mb-3 flex flex-wrap gap-1">
          {STATUS.map((s) => (
            <button key={s.id} type="button" role="tab" aria-selected={status === s.id} onClick={() => setStatus(s.id)}
              className={`rounded-sm px-3 py-1.5 text-sm ${status === s.id ? "bg-petrol text-white" : "text-ink-2 hover:bg-paper"}`}>
              {s.label}
            </button>
          ))}
        </div>
        {d && (
          <div className={t.loading ? "opacity-60" : ""} aria-busy={t.loading}>
            <DataTable<TicketRow> caption="Tickets" rowKey={(r) => r.ticket_id} rows={d.items} dense
              server={{ page: d.page, pageSize: d.page_size, total: d.total, sort: sort.key, order: sort.order,
                onSort: (key, order) => { setSort({ key, order }); setPage(1); }, onPage: setPage }}
              columns={[
                { key: "ticket_id", header: "Ticket", render: (r) => <span className="font-medium">{r.ticket_id}</span> },
                { key: "created_at", header: "Created", render: (r) => fmtDate(r.created_at) },
                { key: "priority", header: "Priority" },
                { key: "subcategory", header: "Issue", sortable: false, render: (r) => r.subcategory ?? r.category },
                { key: "team_name", header: "Team", sortable: false },
                { key: "customer_name", header: "Customer" },
                { key: "ticket_status", header: "Status" },
                { key: "resolution_time_hours", header: "Resolution", align: "right", render: (r) => fmtHours(r.resolution_time_hours) },
                { key: "sla", header: "SLA", sortable: false, render: (r) => <Outcome t={r} /> },
              ]} />
            {t.error && <p className="mt-2 text-sm text-bad">{t.error}</p>}
          </div>
        )}
      </Panel>
    </>
  );
}
