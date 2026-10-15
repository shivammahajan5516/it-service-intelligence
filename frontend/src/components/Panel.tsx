import { useState, type ReactNode } from "react";
import { Activity, Table } from "lucide-react";
import { EmptyState, ErrorState, Loading } from "./States";

interface PanelProps {
  title: string;
  description?: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  empty?: boolean;
  height?: number;
  /** Optional accessible table alternative; adds a chart/table toggle. */
  table?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** A titled section of the dashboard with loading / error / empty states built in. */
export function Panel({ title, description, loading, error, onRetry, empty, height = 260, table, actions,
  className = "", children }: PanelProps) {
  const [showTable, setShowTable] = useState(false);
  let body: ReactNode = children;
  if (error) body = <ErrorState message={error} onRetry={onRetry} />;
  else if (loading) body = <Loading height={height} />;
  else if (empty) body = <EmptyState />;
  else if (showTable && table) body = <div className="max-h-[420px] overflow-auto">{table}</div>;

  return (
    <section className={`panel flex flex-col p-4 sm:p-5 ${className}`} aria-label={title}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          {description && <p className="mt-0.5 max-w-prose text-sm text-ink-2">{description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          {table && !error && !loading && !empty && (
            <button
              type="button"
              onClick={() => setShowTable((v) => !v)}
              className="control inline-flex items-center gap-1.5 text-xs"
              aria-pressed={showTable}
              aria-label={showTable ? `Show ${title} as a chart` : `Show ${title} as a table`}
            >
              {showTable ? <Activity size={14} aria-hidden="true" /> : <Table size={14} aria-hidden="true" />}
              {showTable ? "Chart" : "Table"}
            </button>
          )}
        </div>
      </header>
      <div className="min-h-0 flex-1">{body}</div>
    </section>
  );
}
