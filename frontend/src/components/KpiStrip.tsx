import { ArrowDownRight, ArrowUpRight, Info, Minus } from "lucide-react";
import { fmtSigned } from "../lib/format";

export interface KpiItem {
  label: string;
  value: string;
  /** difference vs previous period, in the KPI's own unit */
  change?: number | null;
  changeUnit?: string;
  changeDigits?: number;
  /** which direction is an improvement */
  better?: "up" | "down" | "neutral";
  help: string;
  sub?: string;
}

function Delta({ item }: { item: KpiItem }) {
  if (item.change === undefined || item.change === null) {
    return <span className="text-xs text-ink-3">No previous period</span>;
  }
  const flat = Math.abs(item.change) < 0.005;
  const improved = item.better === "neutral" || flat ? null
    : (item.change > 0) === (item.better === "up");
  const Icon = flat ? Minus : item.change > 0 ? ArrowUpRight : ArrowDownRight;
  const tone = improved === null ? "text-ink-2" : improved ? "text-good" : "text-bad";
  const word = improved === null ? "change" : improved ? "better" : "worse";
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${tone}`}>
      <Icon size={14} aria-hidden="true" />
      {fmtSigned(item.change, item.changeUnit ?? "", item.changeDigits ?? 1)}
      <span className="sr-only">({word} than previous period)</span>
    </span>
  );
}

/** A single ruled strip of KPIs - one panel, cells divided by rules, not separate cards. */
export function KpiStrip({ items, label }: { items: KpiItem[]; label: string }) {
  return (
    <section aria-label={label} className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-rule bg-rule sm:grid-cols-4 xl:grid-cols-8">
      {items.map((k) => (
        <div key={k.label} className="bg-panel p-4">
          <div className="flex items-center gap-1 text-sm text-ink-2">
            <span>{k.label}</span>
            <span title={k.help} aria-label={`${k.label}: ${k.help}`} className="cursor-help text-ink-3">
              <Info size={13} aria-hidden="true" />
            </span>
          </div>
          <p className="figure mt-1 text-2xl text-ink">{k.value}</p>
          <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2">
            <Delta item={k} />
            {k.sub && <span className="text-xs text-ink-3">{k.sub}</span>}
          </div>
        </div>
      ))}
    </section>
  );
}
