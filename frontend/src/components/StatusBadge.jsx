import React from "react";
import { STATUS_STYLE } from "../config/metrics";

// Colour is never the only signal: every status shows an icon and a word.
export default function StatusBadge({ status = "normal", label }) {
  const style = STATUS_STYLE[status] || STATUS_STYLE.normal;
  const Icon = style.Icon;
  return (
    <span className="status-badge" style={{ "--status-color": style.color }}>
      <Icon size={12} aria-hidden="true" />
      {label || style.label}
    </span>
  );
}

export function statusColor(status) {
  return (STATUS_STYLE[status] || STATUS_STYLE.normal).color;
}
