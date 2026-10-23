import React, { useEffect, useMemo, useState } from "react";
import { ClipboardList, Save } from "lucide-react";
import { getDecisions, recordDecision } from "../services/api";
import { useApp } from "../context/AppContext";
import PageHeader from "../components/PageHeader";
import NextActions from "../components/NextActions";
import { EmptyState, Skeleton } from "../components/Skeleton";

export default function DecisionCenter() {
  const { summary, can, notify, user } = useApp();
  const [decisions, setDecisions] = useState(null);
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState({
    issue: "", recommendation: "", administrator_action: "", department: summary.department === "All departments" ? "Emergency" : summary.department,
  });
  const [saving, setSaving] = useState(false);

  const load = () => getDecisions().then(setDecisions).catch(() => setDecisions([]));
  useEffect(() => { load(); }, []);

  const topAlert = summary.alerts[0];
  useEffect(() => {
    if (topAlert && !form.issue) setForm((f) => ({ ...f, issue: topAlert.reason.split(". ")[0], recommendation: topAlert.suggested_action }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topAlert?.id]);

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await recordDecision({ ...form, outcome: "pending", outcome_details: "Monitoring 48h resolution metrics." });
      notify("Decision recorded in the audit trail");
      setForm((f) => ({ ...f, administrator_action: "" }));
      load();
    } catch (err) {
      notify(err.message, "error");
    } finally {
      setSaving(false);
    }
  }

  const shown = useMemo(() => (decisions || []).filter((d) =>
    !filter || `${d.issue} ${d.administrator_action} ${d.recorded_by} ${d.outcome}`.toLowerCase().includes(filter.toLowerCase())), [decisions, filter]);

  const situation = [
    ["Current situation", `Risk ${summary.risk.score}/100 (${summary.risk.level_label}); top driver: ${summary.risk.top_driver}.`],
    ["Historical memory", `${summary.hindsight.similarity_score}% similar to ${summary.hindsight.date}: ${summary.hindsight.previous_action}`],
    ["Active alerts", summary.alerts.length ? summary.alerts.slice(0, 2).map((a) => a.reason.split(". ")[0]).join(" · ") : "None"],
  ];

  return (
    <div className="page">
      <PageHeader page="decision" />
      <div className="grid grid-2">
        <section className="card">
          <div className="card-title">Situation summary</div>
          <div className="stack">
            {situation.map(([k, v]) => (
              <div className="inset" key={k}><span className="eyebrow">{k}</span><p style={{ margin: "4px 0 0", color: "var(--text)" }}>{v}</p></div>
            ))}
          </div>
        </section>
        <NextActions />
      </div>

      {can("Analyst") ? (
        <form className="card" onSubmit={save} aria-labelledby="record-title">
          <div className="card-title" id="record-title"><Save size={17} aria-hidden="true" /> Record a decision</div>
          <div className="grid grid-2">
            <label className="field">Issue<input type="text" required value={form.issue} onChange={(e) => setForm({ ...form, issue: e.target.value })} /></label>
            <label className="field">Recommendation considered<input type="text" required value={form.recommendation} onChange={(e) => setForm({ ...form, recommendation: e.target.value })} /></label>
            <label className="field">Action taken<input type="text" required placeholder="e.g. Activated discharge lounge and called 2 on-call doctors"
              value={form.administrator_action} onChange={(e) => setForm({ ...form, administrator_action: e.target.value })} /></label>
            <label className="field">Department<input type="text" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></label>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn btn-primary" disabled={saving}>{saving ? "Saving…" : "Record decision"}</button>
            <small>Recorded as {user.full_name || user.username} ({user.role}).</small>
          </div>
        </form>
      ) : (
        <p className="muted">You have view-only access. Analysts and Admins can record decisions.</p>
      )}

      <section className="card">
        <div className="spread" style={{ marginBottom: 10 }}>
          <div className="card-title" style={{ margin: 0 }}><ClipboardList size={17} aria-hidden="true" /> Decision history</div>
          <input type="search" placeholder="Filter decisions" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 240 }} aria-label="Filter decisions" />
        </div>
        {decisions == null ? <Skeleton height={160} /> : shown.length === 0 ? (
          <EmptyState icon={ClipboardList} title={filter ? "No matching decisions" : "No decisions yet"} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>When</th><th>Department</th><th>Issue</th><th>Action</th><th>Status</th><th>By</th></tr></thead>
              <tbody>
                {shown.map((d) => (
                  <tr key={d.id}>
                    <td className="num">{d.timestamp}</td><td>{d.department}</td><td>{d.issue}</td>
                    <td style={{ color: "var(--text)" }}>{d.administrator_action}</td>
                    <td><span className="pill">{d.outcome}</span></td><td>{d.recorded_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
