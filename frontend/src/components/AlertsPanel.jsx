import React, { useEffect, useState } from "react";
import { BellRing, CheckCircle2, X } from "lucide-react";
import { useApp } from "../context/AppContext";
import AlertCard from "./AlertCard";
import Drawer from "./Drawer";

export default function AlertsPanel({ open, onClose }) {
  const { alertsAll, reloadAlerts } = useApp();
  const [tab, setTab] = useState("active");
  useEffect(() => { if (open) reloadAlerts(); }, [open, reloadAlerts]);

  const items = alertsAll.filter((a) => (tab === "active" ? a.state === "active" : a.state !== "active"));
  const activeCount = alertsAll.filter((a) => a.state === "active").length;

  return (
    <Drawer open={open} onClose={onClose} labelledBy="alerts-title">
      <div className="drawer-head">
        <div className="row"><BellRing size={18} aria-hidden="true" /><h2 id="alerts-title" style={{ fontSize: 16 }}>Alerts</h2></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close alerts"><X size={16} /></button>
      </div>
      <div style={{ padding: "12px 18px 0" }}>
        <div className="tabs" role="tablist" aria-label="Alert filter">
          <button role="tab" aria-selected={tab === "active"} onClick={() => setTab("active")}>Active ({activeCount})</button>
          <button role="tab" aria-selected={tab === "handled"} onClick={() => setTab("handled")}>Acknowledged & snoozed</button>
        </div>
      </div>
      <div className="drawer-body" role="tabpanel">
        {items.length === 0 ? (
          <div className="empty">
            <CheckCircle2 size={28} aria-hidden="true" />
            <strong>{tab === "active" ? "No active alerts" : "Nothing handled yet"}</strong>
            <span>{tab === "active" ? "All monitored resources are within safe limits." : "Acknowledged or snoozed alerts appear here."}</span>
          </div>
        ) : items.map((a) => <AlertCard key={a.id} alert={a} />)}
      </div>
    </Drawer>
  );
}
