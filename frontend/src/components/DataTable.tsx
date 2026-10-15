import { useMemo, useState, type ReactNode } from "react";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, ChevronsUpDown } from "lucide-react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  /** value used for client-side sorting; defaults to row[key] */
  value?: (row: T) => number | string | null | undefined;
  align?: "left" | "right";
  sortable?: boolean;
  help?: string;
}

interface ServerPaging {
  page: number;
  pageSize: number;
  total: number;
  sort: string;
  order: "asc" | "desc";
  onSort: (key: string, order: "asc" | "desc") => void;
  onPage: (page: number) => void;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  caption: string;
  initialSort?: { key: string; order: "asc" | "desc" };
  pageSize?: number;
  server?: ServerPaging;
  dense?: boolean;
}

/** Sortable, paginated table. Client-side by default; pass `server` for API-side paging. */
export function DataTable<T>({ columns, rows, rowKey, caption, initialSort, pageSize = 10, server, dense }: Props<T>) {
  const [sort, setSort] = useState(initialSort ?? { key: "", order: "desc" as "asc" | "desc" });
  const [page, setPage] = useState(1);

  const sorted = useMemo(() => {
    if (server || !sort.key) return rows;
    const col = columns.find((c) => c.key === sort.key);
    const get = col?.value ?? ((r: T) => (r as unknown as Record<string, unknown>)[sort.key] as number | string | null);
    return [...rows].sort((a, b) => {
      const va = get(a), vb = get(b);
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb));
      return sort.order === "asc" ? cmp : -cmp;
    });
  }, [rows, sort, columns, server]);

  const curSort = server ? { key: server.sort, order: server.order } : sort;
  const curPage = server ? server.page : page;
  const size = server ? server.pageSize : pageSize;
  const total = server ? server.total : sorted.length;
  const pages = Math.max(1, Math.ceil(total / size));
  const visible = server ? rows : sorted.slice((curPage - 1) * size, curPage * size);

  const onHeader = (c: Column<T>) => {
    if (c.sortable === false) return;
    const order: "asc" | "desc" = curSort.key === c.key && curSort.order === "desc" ? "asc" : "desc";
    if (server) server.onSort(c.key, order);
    else {
      setSort({ key: c.key, order });
      setPage(1);
    }
  };
  const goto = (p: number) => (server ? server.onPage(p) : setPage(p));
  const pad = dense ? "px-3 py-1.5" : "px-3 py-2";

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-rule text-left text-xs text-ink-2">
              {columns.map((c) => {
                const active = curSort.key === c.key;
                const Icon = !active ? ChevronsUpDown : curSort.order === "asc" ? ChevronUp : ChevronDown;
                return (
                  <th key={c.key} scope="col"
                    aria-sort={active ? (curSort.order === "asc" ? "ascending" : "descending") : "none"}
                    className={`${pad} font-medium ${c.align === "right" ? "text-right" : ""}`}>
                    {c.sortable === false ? c.header : (
                      <button type="button" onClick={() => onHeader(c)} title={c.help}
                        className={`inline-flex items-center gap-1 hover:text-ink ${active ? "text-ink" : ""} ${c.align === "right" ? "flex-row-reverse" : ""}`}>
                        {c.header}
                        <Icon size={12} aria-hidden="true" className={active ? "" : "opacity-50"} />
                      </button>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={rowKey(r)} className="border-b border-rule/70 last:border-0 hover:bg-paper">
                {columns.map((c) => (
                  <td key={c.key} className={`${pad} ${c.align === "right" ? "text-right tabular-nums" : ""}`}>
                    {c.render ? c.render(r) : String((r as unknown as Record<string, unknown>)[c.key] ?? "–")}
                  </td>
                ))}
              </tr>
            ))}
            {visible.length === 0 && (
              <tr><td colSpan={columns.length} className="px-3 py-6 text-center text-ink-2">No matching rows.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {total > size && (
        <nav className="mt-3 flex items-center justify-between text-sm text-ink-2" aria-label={`${caption} pages`}>
          <span>
            {((curPage - 1) * size + 1).toLocaleString("en-GB")}–{Math.min(curPage * size, total).toLocaleString("en-GB")} of{" "}
            {total.toLocaleString("en-GB")}
          </span>
          <div className="flex items-center gap-1">
            <button type="button" className="control px-2" onClick={() => goto(curPage - 1)} disabled={curPage <= 1}
              aria-label="Previous page"><ChevronLeft size={16} aria-hidden="true" /></button>
            <span className="px-2">Page {curPage} of {pages}</span>
            <button type="button" className="control px-2" onClick={() => goto(curPage + 1)} disabled={curPage >= pages}
              aria-label="Next page"><ChevronRight size={16} aria-hidden="true" /></button>
          </div>
        </nav>
      )}
    </div>
  );
}
