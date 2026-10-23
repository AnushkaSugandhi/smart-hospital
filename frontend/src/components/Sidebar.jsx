import React from "react";
import { motion } from "framer-motion";
import { GROUPS, PAGES } from "../config/pages";
import { useApp } from "../context/AppContext";

export default function Sidebar({ open, onClose }) {
  const { route, navigate, can, activeAlerts } = useApp();
  const critical = activeAlerts.filter((a) => a.severity === "critical").length;

  return (
    <>
      <div className={`sidebar-backdrop ${open ? "open" : ""}`} onClick={onClose} aria-hidden="true" />
      <nav className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation" data-tour="nav">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">VGH</div>
          <div>
            <strong>SH-DSS</strong>
            <span>Vardhaman General Hospital</span>
          </div>
        </div>

        {GROUPS.map((group) => {
          const pages = PAGES.filter((p) => p.group === group && can(p.minRole));
          if (!pages.length) return null;
          return (
            <div className="nav-group" key={group} role="group" aria-label={group}>
              <div className="nav-label">{group}</div>
              {pages.map(({ key, label, Icon }) => {
                const active = route.page === key;
                return (
                  <button
                    key={key}
                    className={`nav-item ${active ? "active" : ""}`}
                    aria-current={active ? "page" : undefined}
                    onClick={() => { navigate(key); onClose(); }}
                  >
                    {active && (
                      <motion.span layoutId="nav-active" className="nav-active-bg"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }} />
                    )}
                    <Icon size={17} aria-hidden="true" />
                    <span>{label}</span>
                    {key === "overview" && critical > 0 && (
                      <span className="nav-badge" aria-label={`${critical} critical alerts`}>{critical}</span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}

        <div className="sidebar-foot">
          Decision support only. Final clinical and operational judgment rests with hospital staff.
        </div>
      </nav>
    </>
  );
}
