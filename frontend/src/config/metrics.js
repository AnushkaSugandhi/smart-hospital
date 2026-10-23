// Display config. Thresholds and formulas come from the backend (/api/v1/config,
// backend/app/core/config.py); this file only maps statuses to colours/icons.
// DEFAULT_BANDS mirrors the backend so the UI still renders before config loads.

export const DEFAULT_BANDS = { green_below: 70, red_above: 85 };

export const STATUS_STYLE = {
  normal: { label: "Normal", tone: "ok", color: "var(--ok)" },
  warning: { label: "Elevated", tone: "warn", color: "var(--warn)" },
  critical: { label: "Critical", tone: "crit", color: "var(--crit)" },
};

export const RISK_STYLE = {
  low: { label: "Low", tone: "ok" },
  medium: { label: "Medium", tone: "warn" },
  high: { label: "High", tone: "crit" },
  critical: { label: "Critical", tone: "crit" },
};

export function statusForPct(pct, bands = DEFAULT_BANDS) {
  if (pct > bands.red_above) return "critical";
  if (pct >= bands.green_below) return "warning";
  return "normal";
}

export function toneFor(status) {
  return (STATUS_STYLE[status] || STATUS_STYLE.normal).tone;
}
