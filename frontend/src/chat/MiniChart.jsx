import React from "react";
import { useReducedMotion } from "framer-motion";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import useThemeColors from "../hooks/useThemeColors";
import StatusBadge from "../components/StatusBadge";

const STATUSES = new Set(["normal", "warning", "critical"]);

function Tip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <b>{label}</b>
      {payload.filter((p) => p.value != null).map((p) => (
        <div key={p.dataKey}><i style={{ background: p.stroke }} />{p.name}: <b>{p.value}{unit}</b></div>
      ))}
    </div>
  );
}

// Small chart or table rendered inside an answer.
export default function MiniChart({ chart }) {
  const c = useThemeColors();
  const reduce = useReducedMotion();
  if (chart.kind === "line") {
    return (
      <figure className="mini-chart">
        <figcaption>{chart.title}</figcaption>
        <div className="legend" aria-hidden="true">
          <span><i style={{ background: "var(--series-1)" }} />Actual</span>
          <span><i className="dashed" style={{ background: "var(--series-2)", color: "var(--series-2)" }} />Forecast</span>
        </div>
        <div style={{ height: 150 }} role="img" aria-label={`${chart.title}: actual and forecast values`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart.series} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" stroke={c.axis} tick={{ fill: c.muted, fontSize: 10 }} tickLine={false} minTickGap={12} />
              <YAxis stroke={c.axis} tick={{ fill: c.muted, fontSize: 10 }} tickLine={false} axisLine={false} width={40}
                unit={chart.unit} domain={["auto", "auto"]} tickFormatter={(v) => +Number(v).toFixed(0)} />
              <Tooltip content={<Tip unit={chart.unit} />} cursor={{ stroke: c.axis }} />
              <Line dataKey="actual" name="Actual" stroke={c["series-1"]} strokeWidth={2} dot={false} isAnimationActive={!reduce} />
              <Line dataKey="forecast" name="Forecast" stroke={c["series-2"]} strokeWidth={2} strokeDasharray="5 4"
                dot={{ r: 3, fill: c["series-2"], stroke: c["surface-solid"], strokeWidth: 2 }} isAnimationActive={!reduce} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </figure>
    );
  }
  return (
    <figure className="mini-chart">
      <figcaption>{chart.title}</figcaption>
      <div className="table-wrap">
        <table>
          <thead><tr>{chart.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
          <tbody>
            {chart.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j} className={j ? "num" : ""}>{STATUSES.has(cell) ? <StatusBadge status={cell} /> : cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
