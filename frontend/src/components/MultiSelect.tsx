import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

interface Option {
  value: string;
  label: string;
}

interface Props {
  label: string;
  options: Option[];
  selected: string[];
  onChange: (values: string[]) => void;
}

/** Accessible multi-select dropdown (button + listbox of checkboxes). */
export function MultiSelect({ label, options, selected, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);

  const summary =
    selected.length === 0 ? "All"
      : selected.length === 1 ? options.find((o) => o.value === selected[0])?.label ?? selected[0]
        : `${selected.length} selected`;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        id={`${id}-btn`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        onClick={() => setOpen((o) => !o)}
        className={`control inline-flex min-w-[8.5rem] items-center justify-between gap-2 ${selected.length ? "border-petrol text-petrol-700" : ""}`}
      >
        <span className="truncate">
          <span className="text-ink-2">{label}: </span>
          {summary}
        </span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && (
        <div
          id={`${id}-list`}
          role="listbox"
          aria-multiselectable="true"
          aria-labelledby={`${id}-btn`}
          className="absolute left-0 z-30 mt-1 max-h-72 w-64 overflow-auto rounded-sm border border-rule bg-panel py-1 shadow-md"
        >
          {options.map((o) => {
            const on = selected.includes(o.value);
            return (
              <button
                key={o.value}
                type="button"
                role="option"
                aria-selected={on}
                onClick={() => toggle(o.value)}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-paper"
              >
                <span className={`flex h-4 w-4 items-center justify-center rounded-[3px] border ${on ? "border-petrol bg-petrol text-white" : "border-ink-3"}`}>
                  {on && <Check size={12} aria-hidden="true" />}
                </span>
                {o.label}
              </button>
            );
          })}
          {selected.length > 0 && (
            <button type="button" onClick={() => onChange([])}
              className="mt-1 w-full border-t border-rule px-3 py-1.5 text-left text-sm text-petrol hover:bg-paper">
              Clear {label.toLowerCase()}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
