import React from "react";
import { formatUtc } from "../utils/time";

const ACTION_LABELS = {
  login: "Signed in", login_failed: "Failed sign-in", upload_validate: "Validated upload", upload_commit: "Committed upload",
  upload_rollback: "Rolled back upload", decision_create: "Recorded decision", alert_acknowledge: "Acknowledged alert",
  alert_snooze: "Snoozed alert", recommendation_approve: "Approved recommendation", recommendation_dismiss: "Dismissed recommendation",
  audit_export: "Exported audit log", chat_question: "Asked AI",
};
export const actionLabel = (a) => ACTION_LABELS[a] || a.replace(/_/g, " ");

function details(text) {
  if (!text) return "";
  try {
    const obj = JSON.parse(text);
    return Object.entries(obj).filter(([, v]) => v != null && v !== "").map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ");
  } catch {
    return text;
  }
}

export default function AuditTable({ items }) {
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Audit log entries, newest first</caption>
        <thead><tr><th>When</th><th>User</th><th>Role</th><th>Action</th><th>Item</th><th>Details</th></tr></thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              <td className="num" style={{ whiteSpace: "nowrap" }}>{formatUtc(r.timestamp)}</td>
              <td style={{ color: "var(--text)" }}>{r.username}</td>
              <td>{r.role || "—"}</td>
              <td><span className="pill">{actionLabel(r.action)}</span></td>
              <td>{r.entity_type ? `${r.entity_type}${r.entity_id ? ` #${r.entity_id}` : ""}` : "—"}</td>
              <td style={{ maxWidth: 420, whiteSpace: "normal" }}>{details(r.details)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
