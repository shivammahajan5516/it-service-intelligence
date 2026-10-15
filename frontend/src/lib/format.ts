const nf0 = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const DASH = "–";

export function fmtInt(v: number | null | undefined): string {
  return v === null || v === undefined || Number.isNaN(v) ? DASH : nf0.format(v);
}
export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return DASH;
  return `${digits === 2 ? nf2.format(v) : nf1.format(v)}%`;
}
export function fmtHours(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return DASH;
  if (v >= 48) return `${nf1.format(v / 24)} d`;
  return `${nf1.format(v)} h`;
}
export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return DASH;
  return digits === 1 ? nf1.format(v) : nf2.format(v);
}
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
export function fmtMonth(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
}
export function fmtSigned(v: number | null | undefined, unit = "", digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return DASH;
  const s = digits === 2 ? nf2.format(Math.abs(v)) : nf1.format(Math.abs(v));
  return `${v > 0 ? "+" : v < 0 ? "−" : "±"}${s}${unit}`;
}
