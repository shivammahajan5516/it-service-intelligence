// Shared chart styling: validated categorical palette (fixed order), recessive axes, one tooltip.
export const SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
export const PRIORITY_COLOR: Record<string, string> = { P1: SERIES[0], P2: SERIES[1], P3: SERIES[2], P4: SERIES[3] };
export const AXIS = { stroke: "#9aa5ad", fontSize: 12, tickLine: false, axisLine: { stroke: "#dfe3e1" } } as const;
export const GRID = { stroke: "#e8ebe9", strokeDasharray: "0", vertical: false } as const;

interface TooltipEntry {
  name?: string | number;
  value?: number | string | (number | string)[];
  color?: string;
  dataKey?: string | number;
}
interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
  formatter?: (v: number) => string;
  labelFormatter?: (l: string) => string;
}

export function ChartTooltip({ active, payload, label, formatter, labelFormatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const fmt = formatter ?? ((v: number) => String(v));
  return (
    <div className="rounded-sm border border-rule bg-panel px-3 py-2 text-xs shadow-sm">
      {label !== undefined && (
        <p className="mb-1 font-medium text-ink">{labelFormatter ? labelFormatter(String(label)) : label}</p>
      )}
      <ul className="space-y-0.5">
        {payload.map((p) => (
          <li key={String(p.dataKey ?? p.name)} className="flex items-center gap-2 text-ink-2">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
            <span>{p.name}</span>
            <span className="ml-auto pl-3 font-medium tabular-nums text-ink">
              {typeof p.value === "number" ? fmt(p.value) : String(p.value ?? "–")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Small legend rendered in HTML so text stays in ink colours (never the series colour). */
export function Legend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2" aria-label="Legend">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-4"
            style={{ background: i.dashed ? "transparent" : i.color, borderTop: i.dashed ? `2px dashed ${i.color}` : undefined }}
            aria-hidden="true"
          />
          {i.label}
        </li>
      ))}
    </ul>
  );
}
