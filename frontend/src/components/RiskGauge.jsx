import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";
import InfoTip from "./InfoTip";
import StatusBadge, { statusColor } from "./StatusBadge";
import { RISK_STYLE } from "../config/metrics";

const R = 90;
const CX = 110;
const CY = 105;

function polar(pct) {
  const angle = Math.PI * (1 - pct / 100);
  return [CX + R * Math.cos(angle), CY - R * Math.sin(angle)];
}
const ARC = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;

// Semicircle 0-100 gauge that animates to its value; glows when High/Critical.
export default function RiskGauge({ risk, levels = [], compact = false }) {
  const reduce = useReducedMotion();
  const style = RISK_STYLE[risk.level] || RISK_STYLE.low;
  const color = statusColor(style.status);
  const glow = risk.level === "high" || risk.level === "critical";
  const maxContribution = Math.max(...risk.breakdown.map((f) => f.contribution), 1);

  return (
    <div className="gauge-wrap" style={{ "--status-color": color }}>
      <svg className={`gauge ${glow ? "glow" : ""}`} viewBox="0 0 220 125" role="img"
        aria-label={`Resource risk ${risk.score} out of 100, ${risk.level_label}`}>
        <path className="track" d={ARC} />
        <motion.path
          className="fill"
          d={ARC}
          style={{ stroke: color }}
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: Math.max(risk.score, 0.5) / 100 }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
        />
        {levels.filter((l) => l.min > 0).map((l) => {
          const [x1, y1] = polar(l.min);
          const inner = R - 10, outer = R + 10;
          const a = Math.PI * (1 - l.min / 100);
          return (
            <g key={l.key}>
              <line className="tick" x1={CX + inner * Math.cos(a)} y1={CY - inner * Math.sin(a)}
                x2={CX + outer * Math.cos(a)} y2={CY - outer * Math.sin(a)} />
              <text className="tick-label" x={x1 + (x1 < CX ? -14 : 6)} y={y1 - 10}>{l.min}</text>
            </g>
          );
        })}
        <text className="tick-label" x={CX - R - 4} y={CY + 16}>0</text>
        <text className="tick-label" x={CX + R - 10} y={CY + 16}>100</text>
      </svg>
      <div className="gauge-value">
        <strong><AnimatedNumber value={risk.score} decimals={1} duration={1.4} /></strong>
        <span>of 100</span>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <StatusBadge status={style.status} label={`${risk.level_label} risk`} />
        <InfoTip label="How the risk score is calculated">
          Weighted sum of factor pressures (each 0–100). Levels: Low 0–30, Medium 31–60, High 61–80, Critical 81–100.
          {risk.breakdown.map((f) => (
            <span key={f.key} className="tip-line">
              {f.label}: {f.pressure} × {f.weight} = <b>{f.contribution}</b> — {f.formula}
            </span>
          ))}
        </InfoTip>
      </div>
      {!compact && (
        <div className="breakdown" aria-label="Contributing factors">
          {risk.breakdown.map((f, i) => (
            <div className="breakdown-row" key={f.key} title={`${f.label}: pressure ${f.pressure}% × weight ${f.weight}`}>
              <span>{f.label}</span>
              <div className="bar-track">
                <motion.div
                  className="bar"
                  initial={reduce ? false : { width: 0 }}
                  animate={{ width: `${(f.contribution / maxContribution) * 100}%` }}
                  transition={{ duration: 0.9, delay: 0.2 + i * 0.08 }}
                />
              </div>
              <b>+{f.contribution}</b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
