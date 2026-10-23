import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { statusForPct, STATUS_STYLE } from "../config/metrics";
import useThemeColors from "../hooks/useThemeColors";

const W = 960;
const H = 200;
const NODE_W = 170;
const NODE_H = 104;
const XS = [100, 360, 620, 870];
const Y = 110;

const STATUS_TOKEN = { normal: "status-good", warning: "status-warning", critical: "status-critical" };

// Emergency → Wards → ICU → Staff. Edge thickness = size of the propagated
// change; colour = projected status of the receiving node.
export default function CascadeCanvas({ nodes, bands }) {
  const reduce = useReducedMotion();
  const c = useThemeColors();

  const edges = nodes.slice(1).map((to, i) => {
    const from = nodes[i];
    const x1 = XS[i] + NODE_W / 2 - 50;
    const x2 = XS[i + 1] - NODE_W / 2 + 50;
    const mid = (x1 + x2) / 2;
    return {
      key: `${from.key}-${to.key}`,
      d: `M ${x1} ${Y} C ${mid} ${Y - 60}, ${mid} ${Y + 60}, ${x2} ${Y}`,
      width: Math.min(3 + Math.abs(to.change) * 0.45, 18),
      color: c[STATUS_TOKEN[to.status]],
      speed: Math.max(0.9, 4 - Math.abs(to.change) / 8),
      to,
    };
  });

  return (
    <svg className="cascade-svg" viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={nodes.map((n) => `${n.label}: ${n.projected}% projected (${STATUS_STYLE[n.status].label})`).join("; ")}>
      {edges.map((e, i) => (
        <g key={e.key}>
          <path className="edge-bg" d={e.d} strokeWidth={e.width + 6} />
          <motion.path className="edge" d={e.d} stroke={e.color} strokeWidth={e.width}
            initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.8, delay: i * 0.25 }} />
          {!reduce && [0, 1, 2].map((p) => (
            <circle key={p} r={Math.max(3, e.width / 3)} fill={c.text} opacity="0.85">
              <animateMotion dur={`${e.speed}s`} repeatCount="indefinite" begin={`${(p * e.speed) / 3}s`} path={e.d} />
            </circle>
          ))}
          <text x={(XS[i] + XS[i + 1]) / 2} y={Y - 52} textAnchor="middle" className="node-sub" fill={c.muted}>
            {e.to.change >= 0 ? "+" : ""}{e.to.change}% strain
          </text>
        </g>
      ))}
      {nodes.map((n, i) => {
        const color = c[STATUS_TOKEN[n.status]];
        return (
          <motion.g key={n.key} initial={reduce ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.15 }}>
            <rect className="node-box" x={XS[i] - NODE_W / 2} y={Y - NODE_H / 2} width={NODE_W} height={NODE_H} rx="16"
              stroke={color} fill={c["surface-solid"]} />
            <text x={XS[i]} y={Y - 22} textAnchor="middle" className="node-title" fill={c.text}>{n.label}</text>
            <text x={XS[i]} y={Y + 8} textAnchor="middle" className="node-val" fill={c.text}>{n.projected}%</text>
            <text x={XS[i]} y={Y + 28} textAnchor="middle" className="node-sub" fill={c.muted}>
              now {n.current}% · {STATUS_STYLE[n.status].label}
            </text>
          </motion.g>
        );
      })}
    </svg>
  );
}

export function buildCascadeNodes(summary, cascade, changePct, bands) {
  const changeOf = (target) => cascade?.edges?.find((e) => e.target === target)?.change_pct ?? 0;
  const project = (current, change) => Math.min(Math.round(current * (1 + change / 100) * 10) / 10, 100);
  const defs = [
    { key: "emergency", label: "Emergency", current: summary.emergency.pressure_pct, change: Number(changePct) },
    { key: "wards", label: "Wards (beds)", current: summary.beds.occupancy_pct, change: changeOf("bed_occupancy") },
    { key: "icu", label: "ICU", current: summary.icu.occupancy_pct, change: changeOf("icu_pressure") },
    { key: "staff", label: "Staff", current: summary.doctors.pressure_pct, change: changeOf("doctor_workload") },
  ];
  return defs.map((d) => {
    const projected = project(d.current, d.change);
    return { ...d, projected, status: statusForPct(projected, bands) };
  });
}
