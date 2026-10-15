import { RotateCcw } from "lucide-react";
import { monthsBack, useFilters } from "../context/FiltersContext";
import { MultiSelect } from "./MultiSelect";

const PRESETS: { id: string; label: string; months?: number; year?: number; all?: boolean }[] = [
  { id: "3m", label: "Last 3 months", months: 3 },
  { id: "6m", label: "Last 6 months", months: 6 },
  { id: "12m", label: "Last 12 months", months: 12 },
  { id: "2025", label: "2025", year: 2025 },
  { id: "2024", label: "2024", year: 2024 },
  { id: "all", label: "All data", all: true },
];

/** One row of filters above the charts; every page reads the same filter state. */
export function FilterBar({ show = ["date", "priority", "team", "category", "region"] }: { show?: string[] }) {
  const { filters, setFilters, reset, meta } = useFilters();
  if (!meta) return null;

  const presetFor = (): string => {
    for (const p of PRESETS) {
      const [s, e] = range(p);
      if (s === filters.start_date && e === filters.end_date) return p.id;
    }
    return "custom";
  };
  function range(p: (typeof PRESETS)[number]): [string, string] {
    if (!meta) return ["", ""];
    if (p.all) return [meta.min_date, meta.max_date];
    if (p.year) return [`${p.year}-01-01`, `${p.year}-12-31`];
    return [monthsBack(meta.max_date, p.months ?? 6), meta.max_date];
  }
  const active = filters.priority.length + filters.team.length + filters.category.length + filters.region.length;

  return (
    <div className="flex flex-wrap items-end gap-2" role="group" aria-label="Dashboard filters">
      {show.includes("date") && (
        <>
          <label className="flex flex-col text-xs text-ink-2">
            Period
            <select
              className="control mt-1"
              value={presetFor()}
              onChange={(e) => {
                const p = PRESETS.find((x) => x.id === e.target.value);
                if (p) {
                  const [s, en] = range(p);
                  setFilters({ start_date: s, end_date: en });
                }
              }}
            >
              {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              <option value="custom" disabled>Custom range</option>
            </select>
          </label>
          <label className="flex flex-col text-xs text-ink-2">
            From
            <input type="date" className="control mt-1" min={meta.min_date} max={filters.end_date || meta.max_date}
              value={filters.start_date} onChange={(e) => setFilters({ start_date: e.target.value })} />
          </label>
          <label className="flex flex-col text-xs text-ink-2">
            To
            <input type="date" className="control mt-1" min={filters.start_date || meta.min_date} max={meta.max_date}
              value={filters.end_date} onChange={(e) => setFilters({ end_date: e.target.value })} />
          </label>
        </>
      )}
      {show.includes("priority") && (
        <MultiSelect label="Priority" selected={filters.priority} onChange={(v) => setFilters({ priority: v })}
          options={meta.priorities.map((p) => ({ value: p, label: p }))} />
      )}
      {show.includes("team") && (
        <MultiSelect label="Team" selected={filters.team} onChange={(v) => setFilters({ team: v })}
          options={meta.teams.map((t) => ({ value: t.team_id, label: t.team_name }))} />
      )}
      {show.includes("category") && (
        <MultiSelect label="Category" selected={filters.category} onChange={(v) => setFilters({ category: v })}
          options={meta.categories.map((c) => ({ value: c, label: c }))} />
      )}
      {show.includes("region") && (
        <MultiSelect label="Region" selected={filters.region} onChange={(v) => setFilters({ region: v })}
          options={meta.regions.map((r) => ({ value: r, label: r }))} />
      )}
      <button type="button" onClick={reset} className="control inline-flex items-center gap-1.5 text-ink-2"
        aria-label="Reset all filters to the last six months">
        <RotateCcw size={14} aria-hidden="true" />
        Reset{active ? ` (${active})` : ""}
      </button>
    </div>
  );
}
