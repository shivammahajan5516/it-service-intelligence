import { useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Building2, Clock, Database, LayoutDashboard, ListChecks, Menu, Network, Users, X } from "lucide-react";
import { useFilters } from "../context/FiltersContext";
import { fmtDate } from "../lib/format";
import { ErrorState } from "./States";

const NAV = [
  { to: "/", label: "Executive overview", icon: LayoutDashboard, end: true },
  { to: "/sla", label: "SLA performance", icon: Clock },
  { to: "/root-causes", label: "Root causes", icon: Network },
  { to: "/teams", label: "Team performance", icon: Users },
  { to: "/customers", label: "Customers", icon: Building2 },
  { to: "/tickets", label: "Tickets", icon: ListChecks },
  { to: "/data-quality", label: "Data quality", icon: Database },
];

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { meta } = useFilters();
  const { search } = useLocation();
  return (
    <div className="flex h-full flex-col bg-ink text-white">
      <div className="px-5 pb-6 pt-6">
        <p className="text-lg font-semibold leading-tight">Service Intelligence</p>
        <p className="mt-1 text-sm text-white/60">Northbridge Managed Services</p>
      </div>
      <nav aria-label="Main" className="flex-1 space-y-0.5 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={{ pathname: to, search }} end={end} onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-sm px-3 py-2 text-sm ${isActive
                ? "bg-white/10 font-medium text-white shadow-[inset_3px_0_0_#5fb3bf]"
                : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
            <Icon size={17} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 px-5 py-4 text-xs leading-relaxed text-white/55">
        <p>Synthetic data for a fictional company. No real customers or people.</p>
        {meta && <p className="mt-1">Extract taken {fmtDate(meta.snapshot_at.slice(0, 10))}</p>}
      </div>
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { metaError, reloadMeta } = useFilters();
  const loc = useLocation();
  const current = NAV.find((n) => (n.end ? loc.pathname === n.to : loc.pathname.startsWith(n.to)));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-panel focus:p-2">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-screen lg:block">
        <Sidebar />
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-64">
            <button type="button" onClick={() => setOpen(false)} aria-label="Close navigation"
              className="absolute right-3 top-5 text-white/70 hover:text-white"><X size={20} /></button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
      <div className="min-w-0">
        <header className="flex items-center gap-3 border-b border-rule bg-panel px-4 py-3 lg:hidden">
          <button type="button" onClick={() => setOpen(true)} aria-label="Open navigation" className="control px-2">
            <Menu size={18} aria-hidden="true" />
          </button>
          <span className="font-semibold">{current?.label ?? "Service Intelligence"}</span>
        </header>
        <main id="main" className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8">
          {metaError ? (
            <ErrorState message={metaError} onRetry={reloadMeta} />
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}

export function PageHeader({ title, intro, children }: { title: string; intro: string; children?: ReactNode }) {
  return (
    <div className="mb-6 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        <p className="mt-1 max-w-3xl text-ink-2">{intro}</p>
      </div>
      {children}
    </div>
  );
}
