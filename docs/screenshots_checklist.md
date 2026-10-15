# Screenshots checklist for the portfolio

Save screenshots to `docs/screenshots/` (create the folder) and reference them in the README. Use a
browser window about 1440 px wide, the default filters (last six months), and light mode. Crop out
the browser chrome.

| # | File name | What to capture | Why it matters |
|---|---|---|---|
| 1 | `01_overview.png` | Executive overview: headline sentence, KPI strip with changes, first two charts | The stakeholder story in one image |
| 2 | `02_overview_filtered.png` | Overview with Team = Network Operations and Priority = P1, P2 | Shows filters working and the URL changing |
| 3 | `03_sla.png` | SLA performance: compliance by priority, breaches by category, team compliance | SLA analysis |
| 4 | `04_sla_table_view.png` | Any SLA chart switched to **Table** view | Accessibility: data is not only visual |
| 5 | `05_root_causes_pareto.png` | Root causes: Pareto with cumulative line and 80% reference | Pareto analysis |
| 6 | `06_root_cause_matrix.png` | Root cause × priority heatmap | Matrix analysis |
| 7 | `07_teams.png` | Team scorecard table and metric-selector bar chart | Team comparison |
| 8 | `08_customers.png` | Customer highlights and table with "At risk" badges, sorted by breach rate | Customer intelligence |
| 9 | `09_tickets.png` | Tickets page with the "Breached" tab | Drill-down |
| 10 | `10_error_state.png` | Any page with the API stopped, showing the error and Try again | Robust UX |
| 11 | `11_mobile.png` | Overview at 375 px with the navigation drawer open | Responsive design |
| 12 | `12_api_docs.png` | `http://localhost:8000/docs` Swagger UI, with `/api/overview` expanded | API documentation |
| 13 | `13_sql_result.png` | VS Code with a query from `database/queries/` and its result (SQLTools) | SQL skills |
| 14 | `14_python_figure.png` | `analytics/outputs/figures/10_team_load_vs_breach.png` | Statistical analysis |
| 15 | `15_model.png` | `analytics/outputs/figures/13_model_roc_pr.png` | Predictive modelling |
| 16 | `16_powerbi_overview.png` | Power BI Executive overview page (if built) | BI tool skills |
| 17 | `17_powerbi_model.png` | Power BI Model view showing the star schema | Data modelling |
| 18 | `18_tests.png` | Terminal output of `pytest tests -q` and the database build's 15 PASS checks | Quality engineering |

In the README, use 4–6 of these. Overview, Pareto, Teams, Customers and Power BI work best; link the
rest from a "More screenshots" section.
