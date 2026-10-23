import React from "react";
import { motion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";
import InfoTip from "./InfoTip";
import Sparkline from "./Sparkline";
import StatusBadge, { statusColor } from "./StatusBadge";
import TrendDelta from "./TrendDelta";

export const cardMotion = {
  hidden: { opacity: 0, y: 14 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.45, ease: [0.22, 1, 0.36, 1] } }),
};

export default function KpiCard({
  title, value, decimals = 0, suffix = "", unit, subtitle, status, info, trend, series, index = 0, format,
}) {
  const color = statusColor(status);
  return (
    <motion.article
      className="card lift kpi"
      variants={cardMotion}
      initial="hidden"
      animate="show"
      custom={index}
      style={{ "--status-color": color }}
      aria-label={title}
    >
      <span className="kpi-accent" aria-hidden="true" />
      <div className="kpi-head">
        <div className="kpi-title">
          {title}
          {info && <InfoTip label={`How ${title.toLowerCase()} is calculated`}>{info}</InfoTip>}
        </div>
        <StatusBadge status={status} />
      </div>
      <div className="kpi-value">
        <AnimatedNumber value={value} decimals={decimals} />
        {suffix}
        {unit && <span className="kpi-unit">{unit}</span>}
      </div>
      {series && <Sparkline data={series} color={color} label={`${title} last ${series.length} days`} format={format} />}
      <div className="kpi-foot">
        <span className="kpi-sub">{subtitle}</span>
        <TrendDelta trend={trend} />
      </div>
    </motion.article>
  );
}
