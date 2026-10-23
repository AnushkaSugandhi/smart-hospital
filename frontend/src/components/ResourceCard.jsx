import React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertTriangle, Database } from "lucide-react";
import AnimatedNumber from "./AnimatedNumber";
import InfoTip from "./InfoTip";
import StatusBadge, { statusColor } from "./StatusBadge";
import TrendDelta from "./TrendDelta";
import { cardMotion } from "./KpiCard";

export default function ResourceCard({ card, index = 0 }) {
  const reduce = useReducedMotion();
  if (!card.available) {
    return (
      <motion.article className="card resource" variants={cardMotion} initial="hidden" animate="show" custom={index}>
        <div className="card-title">{card.label}</div>
        <div className="empty" style={{ padding: "8px 0" }}>
          <Database size={22} aria-hidden="true" />
          <span style={{ fontSize: 12 }}>No data yet. Add the optional {card.label.toLowerCase()} columns to your next upload.</span>
        </div>
      </motion.article>
    );
  }

  const color = statusColor(card.status);
  const meterPct = card.total ? Math.min((card.used / card.total) * 100, 100) : null;
  const decimals = Number.isInteger(card.value) ? 0 : 1;

  return (
    <motion.article className="card lift resource" variants={cardMotion} initial="hidden" animate="show" custom={index}
      style={{ "--status-color": color }} aria-label={card.label}>
      <div className="spread">
        <div className="kpi-title">{card.label}<InfoTip label={`About ${card.label}`}>{card.formula}</InfoTip></div>
        <StatusBadge status={card.status} label={card.low_stock && card.status !== "normal" ? (card.key === "nurses" ? "Short" : "Low") : undefined} />
      </div>
      <div className="kpi-value" style={{ fontSize: 26, marginTop: 6 }}>
        <AnimatedNumber value={card.value} decimals={decimals} />
        {card.unit === "%" ? "%" : <span className="kpi-unit">{card.unit}</span>}
      </div>
      {meterPct != null && (
        <div className="meter" role="img" aria-label={`${card.used} of ${card.total} in use`}>
          <motion.div initial={reduce ? false : { width: 0 }} animate={{ width: `${meterPct}%` }} transition={{ duration: 0.9 }} />
        </div>
      )}
      {card.groups && (
        <div className="blood-grid">
          {card.groups.map((g) => (
            <div key={g.group} className="blood-cell" style={{ "--status-color": statusColor(g.status) }}
              title={`${g.group}: ${g.units} units (${g.status_label})`}>
              <span>{g.group}</span>
              <b className="num">{g.units}</b>
              {g.status !== "normal" && <span className="sr-only">{g.status_label}</span>}
            </div>
          ))}
        </div>
      )}
      <div className="kpi-foot" style={{ marginTop: 8 }}>
        <span className="kpi-sub">{card.summary}</span>
        <TrendDelta trend={card.trend} />
      </div>
      {card.warning && (
        <div className="warn-line" style={{ marginTop: 8 }}>
          <AlertTriangle size={13} aria-hidden="true" style={{ color }} /> {card.warning}
        </div>
      )}
    </motion.article>
  );
}
