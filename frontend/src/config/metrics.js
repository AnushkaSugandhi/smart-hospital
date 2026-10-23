// Display config. Thresholds and formulas come from the backend (/api/v1/config,
// backend/app/core/config.py); this file only maps statuses to colours, icons
// and labels. DEFAULT_BANDS mirrors the backend so the UI can render before the
// config request returns.
import { AlertOctagon, AlertTriangle, CheckCircle2 } from "lucide-react";

export const DEFAULT_BANDS = { green_below: 70, red_above: 85 };

// Status colours are fixed (never themed) and always paired with icon + label.
export const STATUS_STYLE = {
  normal: { label: "Normal", tone: "ok", color: "var(--status-good)", Icon: CheckCircle2 },
  warning: { label: "Elevated", tone: "warn", color: "var(--status-warning)", Icon: AlertTriangle },
  critical: { label: "Critical", tone: "crit", color: "var(--status-critical)", Icon: AlertOctagon },
};

export const RISK_STYLE = {
  low: { label: "Low", status: "normal" },
  medium: { label: "Medium", status: "warning" },
  high: { label: "High", status: "critical" },
  critical: { label: "Critical", status: "critical" },
};

export const SEVERITY_STATUS = { critical: "critical", warning: "warning", info: "normal" };

export function statusForPct(pct, bands = DEFAULT_BANDS) {
  if (pct > bands.red_above) return "critical";
  if (pct >= bands.green_below) return "warning";
  return "normal";
}

export function toneFor(status) {
  return (STATUS_STYLE[status] || STATUS_STYLE.normal).tone;
}

// KPI definitions for the Overview cards. `history` is the key in
// /resources/history rows; `scale` turns stored ratios into display units.
export const KPI_CARDS = [
  {
    key: "bed_occupancy", title: "Bed occupancy", block: "beds", history: "bed_occupancy", scale: 100,
    value: (d) => d.beds.occupancy_pct, suffix: "%", decimals: 1,
    subtitle: (d) => `${d.beds.available} of ${d.beds.total} beds free`,
  },
  {
    key: "icu_occupancy", title: "ICU occupancy", block: "icu", history: "icu_occupancy", scale: 100,
    value: (d) => d.icu.occupancy_pct, suffix: "%", decimals: 1,
    subtitle: (d) => `${d.icu.available} of ${d.icu.total} ICU beds free`,
  },
  {
    key: "doctor_workload", title: "Doctor workload", block: "doctors", history: "doctor_workload", scale: 1,
    value: (d) => d.doctors.average_patients_per_doctor, unit: "patients per doctor", decimals: 1,
    subtitle: (d) => `About ${d.doctors.overloaded} of ${d.doctors.total} doctors overloaded (est.)`,
  },
  {
    key: "emergency_cases", title: "Emergency cases", block: "emergency", history: "emergency_cases", scale: 1,
    value: (d) => d.emergency.active_cases, unit: "active cases", decimals: 0,
    subtitle: (d) => `${d.emergency.pressure_pct}% pressure · ${d.emergency.active_cases} of ${d.emergency.capacity} ED bays`,
  },
];
