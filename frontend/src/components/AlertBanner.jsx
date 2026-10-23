import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertOctagon, X } from "lucide-react";
import { useApp } from "../context/AppContext";

// Top banner for the most urgent active critical alert.
export default function AlertBanner({ onOpen }) {
  const { activeAlerts } = useApp();
  const [hidden, setHidden] = useState(() => new Set());
  const critical = activeAlerts.filter((a) => a.severity === "critical" && !hidden.has(a.id));
  const top = critical[0];

  return (
    <AnimatePresence>
      {top && (
        <motion.div
          className="alert-banner"
          role="alert"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
        >
          <AlertOctagon size={18} aria-hidden="true" />
          <div className="msg">
            <strong>Critical · {top.resource_type}</strong>
            {top.reason.split(". ")[0]}.
            {critical.length > 1 && <span className="muted"> (+{critical.length - 1} more)</span>}
          </div>
          <button className="btn btn-sm" onClick={onOpen}>View alerts</button>
          <button className="icon-btn" style={{ width: 30, height: 30 }} aria-label="Hide this banner"
            onClick={() => setHidden((s) => new Set(s).add(top.id))}>
            <X size={14} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
