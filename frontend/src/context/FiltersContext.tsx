// Global dashboard filters, stored in the URL so views are shareable and survive refresh.
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../lib/useApi";
import type { FilterState, Meta } from "../lib/types";

interface FiltersCtx {
  filters: FilterState;
  setFilters: (patch: Partial<FilterState>) => void;
  reset: () => void;
  meta: Meta | null;
  metaError: string | null;
  reloadMeta: () => void;
}

const Ctx = createContext<FiltersCtx | null>(null);
const LIST_KEYS = ["priority", "team", "category", "region"] as const;

export function monthsBack(maxDate: string, months: number): string {
  const d = new Date(`${maxDate}T00:00:00`);
  const start = new Date(d.getFullYear(), d.getMonth() - months + 1, 1);
  return `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-01`;
}

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const metaState = useApi<Meta>("/api/meta");
  const meta = metaState.data;

  // Default view: the last six months of data, compared with the six months before.
  useEffect(() => {
    if (meta && !params.get("start_date") && !params.get("end_date")) {
      const next = new URLSearchParams(params);
      next.set("start_date", monthsBack(meta.max_date, 6));
      next.set("end_date", meta.max_date);
      setParams(next, { replace: true });
    }
  }, [meta, params, setParams]);

  const filters: FilterState = useMemo(
    () => ({
      start_date: params.get("start_date") ?? "",
      end_date: params.get("end_date") ?? "",
      priority: params.getAll("priority"),
      team: params.getAll("team"),
      category: params.getAll("category"),
      region: params.getAll("region"),
    }),
    [params],
  );

  const setFilters = useCallback(
    (patch: Partial<FilterState>) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            next.delete(k);
            if (Array.isArray(v)) v.forEach((x) => next.append(k, x));
            else if (v) next.set(k, v);
          }
          return next;
        },
        { replace: false },
      );
    },
    [setParams],
  );

  const reset = useCallback(() => {
    const next = new URLSearchParams();
    if (meta) {
      next.set("start_date", monthsBack(meta.max_date, 6));
      next.set("end_date", meta.max_date);
    }
    LIST_KEYS.forEach((k) => next.delete(k));
    setParams(next);
  }, [meta, setParams]);

  const value = useMemo(
    () => ({ filters, setFilters, reset, meta, metaError: metaState.error, reloadMeta: metaState.reload }),
    [filters, setFilters, reset, meta, metaState.error, metaState.reload],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFilters(): FiltersCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useFilters must be used inside FiltersProvider");
  return c;
}

/** True once the default date range has been applied (avoids a wasted first request). */
export function useFiltersReady(): boolean {
  const { filters, meta, metaError } = useFilters();
  return Boolean(metaError) || Boolean(meta && filters.start_date && filters.end_date);
}
