import React, { useEffect, useState } from "react";
import { Info } from "lucide-react";
import { analyzeCascade } from "../services/api";
import { useApp } from "../context/AppContext";
import PageHeader from "../components/PageHeader";
import CascadeCanvas, { buildCascadeNodes } from "../components/CascadeCanvas";
import { Skeleton } from "../components/Skeleton";

export default function CascadeFlow() {
  const { summary, config, route, navigate } = useApp();
  const [change, setChange] = useState(Number(route.params.change_pct) || 20);
  const [cascade, setCascade] = useState(null);

  useEffect(() => {
    const id = setTimeout(() => {
      analyzeCascade({ driver: "admissions", change_pct: change, department: "Emergency" }).then(setCascade).catch(() => {});
    }, 200);
    return () => clearTimeout(id);
  }, [change]);

  const nodes = cascade ? buildCascadeNodes(summary, cascade, change, config?.status_bands) : null;

  return (
    <div className="page">
      <PageHeader page="cascade">
        <button className="btn" onClick={() => navigate("whatif", { admissions_change_pct: change })}>Run in simulator</button>
      </PageHeader>
      <section className="card">
        <div className="slider-row" style={{ maxWidth: 520 }}>
          <div className="spread">
            <label htmlFor="surge">Emergency admissions change</label>
            <b>{change > 0 ? "+" : ""}{change}%</b>
          </div>
          <input id="surge" type="range" min="-20" max="60" step="5" value={change} onChange={(e) => setChange(Number(e.target.value))} />
        </div>
        <p className="card-sub" style={{ marginTop: 6 }}>
          Line thickness shows how much strain flows to the next area; colour shows that area's projected status
          (green below {config?.status_bands?.green_below ?? 70}%, amber to {config?.status_bands?.red_above ?? 85}%, red above).
        </p>
        {nodes ? <CascadeCanvas nodes={nodes} /> : <Skeleton height={260} />}
      </section>

      {cascade && (
        <section className="card">
          <div className="card-title">Why strain spreads</div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>From</th><th>To</th><th>Factor</th><th>Expected change</th><th>Reason</th></tr></thead>
              <tbody>
                {cascade.edges.map((e) => (
                  <tr key={e.target}>
                    <td>{e.source.replace(/_/g, " ")}</td>
                    <td style={{ color: "var(--text)" }}>{e.target.replace(/_/g, " ")}</td>
                    <td className="num">× {e.factor}</td>
                    <td className="num">{e.change_pct > 0 ? "+" : ""}{e.change_pct}%</td>
                    <td>{e.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="disclaimer" style={{ marginTop: 10 }}><Info size={14} aria-hidden="true" />{cascade.note}</div>
        </section>
      )}
    </div>
  );
}
