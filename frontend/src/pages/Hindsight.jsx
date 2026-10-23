import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { History } from "lucide-react";
import { searchHindsight } from "../services/api";
import { useApp } from "../context/AppContext";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import { EmptyState, Skeleton } from "../components/Skeleton";
import { cardMotion } from "../components/KpiCard";

const LABELS = {
  admissions: "Admissions", emergency_cases: "Emergency cases", bed_occupancy: "Bed occupancy",
  icu_occupancy: "ICU occupancy", doctor_workload: "Patients per doctor", staff_workload: "Patients per staff",
};
const fmt = (k, v) => (k.endsWith("occupancy") ? `${(v * 100).toFixed(1)}%` : v);

export default function Hindsight() {
  const { summary } = useApp();
  const [data, setData] = useState(null);
  useEffect(() => { searchHindsight().then(setData).catch(() => setData({ matches: [] })); }, [summary?.generated_at]);

  return (
    <div className="page">
      <PageHeader page="hindsight" />
      {data?.current && (
        <section className="card">
          <div className="card-title">Today's profile used for matching</div>
          <div className="stat-grid">
            {Object.entries(data.current).map(([k, v]) => (
              <div className="stat" key={k}><span>{LABELS[k] || k}</span><b>{fmt(k, v)}</b></div>
            ))}
          </div>
        </section>
      )}
      {!data ? <Skeleton height={200} /> : data.matches.length === 0 ? (
        <EmptyState icon={History} title="No past events yet">Historical events appear here once they are recorded.</EmptyState>
      ) : data.matches.map((m, i) => (
        <motion.article key={`${m.date}-${i}`} className="card lift history-card" variants={cardMotion} initial="hidden" animate="show" custom={i}>
          <div className="similarity">
            <span className="eyebrow">Similarity</span>
            <strong>{m.similarity_score}%</strong>
            <div className="bar-track" aria-hidden="true"><div className="bar" style={{ width: `${m.similarity_score}%` }} /></div>
            <small>{m.date} · {m.department}</small>
          </div>
          <div className="stack">
            <h3 style={{ fontSize: 15 }}>{m.situation}</h3>
            <p style={{ margin: 0 }}><b>What was done:</b> {m.previous_action}</p>
            <p style={{ margin: 0 }}><b>Outcome:</b> {m.outcome}</p>
            <StatusBadge status={m.outcome_status === "resolved" ? "normal" : "warning"} label={m.outcome_status} />
          </div>
        </motion.article>
      ))}
      {data?.note && <p className="muted" style={{ fontSize: 12 }}>{data.note}</p>}
    </div>
  );
}
