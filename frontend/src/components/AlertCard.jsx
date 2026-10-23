import React, { useState } from "react";
import { BellOff, Check, TrendingUp } from "lucide-react";
import { parseUtc } from "../utils/time";
import { acknowledgeAlert, snoozeAlert } from "../services/api";
import { useApp } from "../context/AppContext";
import { SEVERITY_STATUS } from "../config/metrics";
import StatusBadge, { statusColor } from "./StatusBadge";

const KIND_LABEL = { threshold: "Threshold", predictive: "Predicted", stock: "Low stock" };

export default function AlertCard({ alert, compact = false }) {
  const { can, reloadAlerts, notify } = useApp();
  const [busy, setBusy] = useState(false);
  const [snooze, setSnooze] = useState(60);
  const status = SEVERITY_STATUS[alert.severity] || "warning";
  const active = alert.state === "active";

  async function run(fn, message) {
    setBusy(true);
    try {
      await fn();
      notify(message);
      await reloadAlerts();
    } catch (e) {
      notify(e.message || "Could not update the alert.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className={`alert-item ${active && alert.severity === "critical" ? "pulse" : ""}`}
      style={{ "--status-color": statusColor(status) }}
      aria-label={`${alert.severity} alert: ${alert.resource_type}`}
    >
      <div className="spread">
        <div className="row">
          <StatusBadge status={status} label={alert.severity === "critical" ? "Critical" : "Warning"} />
          <strong style={{ fontSize: 13 }}>{alert.resource_type}</strong>
        </div>
        <span className="kind-tag">
          {alert.kind === "predictive" && <TrendingUp size={11} aria-hidden="true" />} {KIND_LABEL[alert.kind] || "Alert"}
        </span>
      </div>
      <p className="reason"><b>Why: </b>{compact ? alert.reason.split(". ")[0] + "." : alert.reason}</p>
      <p className="action"><b>Suggested action: </b>{alert.suggested_action}</p>
      {!active && (
        <span className="meta">
          {alert.state === "acknowledged" ? "Acknowledged" : `Snoozed until ${parseUtc(alert.snoozed_until).toLocaleTimeString()}`}
          {alert.handled_by ? ` by ${alert.handled_by}` : ""}
        </span>
      )}
      {active && !compact && can("Analyst") && (
        <div className="row-wrap">
          <button className="btn btn-sm btn-primary" disabled={busy}
            onClick={() => run(() => acknowledgeAlert(alert.id), "Alert acknowledged")}>
            <Check size={14} /> Acknowledge
          </button>
          <label className="sr-only" htmlFor={`snooze-${alert.id}`}>Snooze duration</label>
          <select id={`snooze-${alert.id}`} value={snooze} onChange={(e) => setSnooze(Number(e.target.value))} style={{ padding: "5px 8px", fontSize: 12 }}>
            <option value={30}>30 min</option>
            <option value={60}>1 hour</option>
            <option value={240}>4 hours</option>
          </select>
          <button className="btn btn-sm" disabled={busy}
            onClick={() => run(() => snoozeAlert(alert.id, snooze), "Alert snoozed")}>
            <BellOff size={14} /> Snooze
          </button>
        </div>
      )}
    </article>
  );
}
