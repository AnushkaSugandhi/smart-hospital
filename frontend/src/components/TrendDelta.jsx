import React from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

// Arrow + % change vs previous period. Green when improving, red when worsening.
export default function TrendDelta({ trend }) {
  if (!trend || trend.change_pct == null) return <span className="delta flat">No previous data</span>;
  const { direction, improving, change_pct, period } = trend;
  const Icon = direction === "up" ? ArrowUpRight : direction === "down" ? ArrowDownRight : ArrowRight;
  const tone = improving == null ? "flat" : improving ? "good" : "bad";
  const word = improving == null ? "no change" : improving ? "improving" : "worsening";
  return (
    <span className={`delta ${tone}`} title={`${word} vs ${period}`}>
      <Icon size={14} aria-hidden="true" />
      {change_pct > 0 ? "+" : ""}{change_pct}%
      <span className="sr-only"> vs {period}, {word}</span>
    </span>
  );
}
