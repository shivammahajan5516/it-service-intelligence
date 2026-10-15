import { useApi } from "../lib/useApi";
import type { DataQuality } from "../lib/types";
import { fmtInt } from "../lib/format";
import { PageHeader } from "../components/Layout";
import { Panel } from "../components/Panel";
import { DataTable } from "../components/DataTable";

export default function DataQualityPage() {
  const q = useApi<DataQuality>("/api/data-quality");
  const d = q.data;
  return (
    <>
      <PageHeader title="Data quality"
        intro="Every correction or exclusion the data pipeline made, and the business rule behind it. Nothing is changed silently." />
      <Panel title={d ? `${fmtInt(d.total_issues)} issues logged` : "Issues logged"} loading={q.loading} error={q.error}
        onRetry={q.reload} empty={!!d && d.rules.length === 0}>
        {d && (
          <DataTable caption="Data quality rules" rowKey={(r) => `${r.rule_id}|${r.issue}`} rows={d.rules} pageSize={25}
            initialSort={{ key: "records", order: "desc" }} columns={[
              { key: "rule_id", header: "Rule" },
              { key: "issue", header: "Issue found" },
              { key: "action", header: "What the pipeline did" },
              { key: "records", header: "Records", align: "right", render: (r) => fmtInt(r.records) },
            ]} />
        )}
      </Panel>
    </>
  );
}
