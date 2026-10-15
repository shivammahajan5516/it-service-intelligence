import { Inbox, RefreshCw, TriangleAlert } from "lucide-react";

export function Skeleton({ height = 220, className = "" }: { height?: number; className?: string }) {
  return <div className={`skeleton rounded-sm ${className}`} style={{ height }} aria-hidden="true" />;
}

export function Loading({ label = "Loading data", height = 220 }: { label?: string; height?: number }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{label}</span>
      <Skeleton height={height} />
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-sm border border-bad/30 bg-bad/5 p-4 text-sm">
      <div className="flex items-start gap-2 text-bad">
        <TriangleAlert size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
        <p>
          <span className="font-medium">Couldn't load this view.</span> {message}
        </p>
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="control inline-flex items-center gap-2">
          <RefreshCw size={14} aria-hidden="true" /> Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message = "No tickets match these filters. Widen the date range or clear a filter." }: { message?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-sm border border-dashed border-rule p-6 text-sm text-ink-2">
      <Inbox size={18} aria-hidden="true" className="shrink-0" />
      <p>{message}</p>
    </div>
  );
}
