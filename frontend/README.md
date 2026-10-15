# Frontend - React dashboard

React 18 + TypeScript + Vite + Tailwind CSS + Recharts + React Router + Lucide. **Synthetic data.**
All numbers come from the API; nothing is hard-coded.

```bash
npm install
npm run dev        # http://localhost:5173   (API must be running on :8000)
npm run build      # type-check + production build into dist/
```

The API address comes from `VITE_API_BASE_URL` in the project-root `.env` (`vite.config.ts` sets
`envDir: '..'`).

| Path | Contents |
|---|---|
| `src/pages/` | Overview, SLA performance, Root causes, Team performance, Customers, Tickets, Data quality |
| `src/components/` | Layout (sidebar, mobile drawer), FilterBar, MultiSelect, KpiStrip, Panel (loading, error, empty and table views), DataTable (sort and paging), chart helpers |
| `src/context/FiltersContext.tsx` | Shared filters stored in the URL, so views can be shared |
| `src/lib/` | Typed API client, `useApi` hook (abortable), formatters, response types |

**Design choices.**
- **Colour:** the validated categorical palette, used in a fixed order. Status colours always come
  with an icon or text.
- **Charts:** one axis per chart, and a table view for every chart.
- **Accessibility:** visible keyboard focus, `aria-sort` on sortable columns, and respect for the
  reduced-motion setting.
