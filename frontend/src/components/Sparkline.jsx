import React, { useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

// Compact trend line that draws itself. Hover/focus shows the value per day.
export default function Sparkline({ data = [], color, height = 40, format = (v) => v, label = "Trend" }) {
  const reduce = useReducedMotion();
  const [hover, setHover] = useState(null);
  const width = 200;
  const pad = 5;

  const points = useMemo(() => {
    const values = data.map((d) => d.value).filter((v) => v != null);
    if (values.length < 2) return [];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    return data.map((d, i) => ({
      ...d,
      x: (i / (data.length - 1)) * width,
      y: pad + (1 - (d.value - min) / span) * (height - pad * 2),
    }));
  }, [data, height]);

  if (points.length < 2) return <div className="sparkline" style={{ height }} aria-hidden="true" />;

  const line = points.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const area = `${line} L${width},${height} L0,${height} Z`;
  const last = points[points.length - 1];
  const active = hover != null ? points[hover] : null;

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
    setHover(Math.round(ratio * (points.length - 1)));
  }

  return (
    <div
      className="sparkline"
      style={{ height, "--status-color": color }}
      onMouseMove={onMove}
      onMouseLeave={() => setHover(null)}
      role="img"
      aria-label={`${label}: ${points.length} days, from ${format(points[0].value)} to ${format(last.value)}`}
    >
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <motion.path
          className="area"
          d={area}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 0.1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        />
        <motion.path
          className="line"
          d={line}
          vectorEffect="non-scaling-stroke"
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.1, ease: "easeOut" }}
        />
        {active && <line x1={active.x} x2={active.x} y1={0} y2={height} stroke="var(--axis)" strokeWidth="1" vectorEffect="non-scaling-stroke" />}
      </svg>
      {/* Dots are HTML so they stay round with preserveAspectRatio="none". */}
      <span
        className="spark-dot"
        style={{ position: "absolute", left: `${(last.x / width) * 100}%`, top: last.y, width: 8, height: 8, marginLeft: -4, marginTop: -4, borderRadius: "50%", background: color, boxShadow: "0 0 0 2px var(--surface-solid)" }}
      />
      {active && (
        <>
          <span style={{ position: "absolute", left: `${(active.x / width) * 100}%`, top: active.y, width: 8, height: 8, marginLeft: -4, marginTop: -4, borderRadius: "50%", background: "var(--text)", boxShadow: "0 0 0 2px var(--surface-solid)" }} />
          <span className="spark-tip" style={{ left: `${(active.x / width) * 100}%` }}>
            {active.label}: <b>{format(active.value)}</b>
          </span>
        </>
      )}
    </div>
  );
}
