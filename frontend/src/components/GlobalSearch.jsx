import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { getDecisions } from "../services/api";
import { PAGES } from "../config/pages";
import { useApp } from "../context/AppContext";

// Ctrl/Cmd+K palette over pages, alerts, resources and decisions.
export default function GlobalSearch({ open, onClose, onOpenAlerts }) {
  const { navigate, alertsAll, summary, can } = useApp();
  const [q, setQ] = useState("");
  const [decisions, setDecisions] = useState([]);
  const [index, setIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setIndex(0);
    setTimeout(() => inputRef.current?.focus(), 30);
    getDecisions().then(setDecisions).catch(() => {});
  }, [open]);

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    const items = [
      ...PAGES.filter((p) => can(p.minRole)).map((p) => ({
        type: "Page", title: p.label, detail: p.description, run: () => navigate(p.key),
      })),
      ...alertsAll.map((a) => ({
        type: "Alert", title: `${a.resource_type} · ${a.severity}`, detail: a.reason, run: onOpenAlerts,
      })),
      ...(summary?.resources || []).filter((r) => r.available).map((r) => ({
        type: "Resource", title: r.label, detail: r.summary, run: () => navigate("overview"),
      })),
      ...decisions.slice(0, 40).map((d) => ({
        type: "Decision", title: d.administrator_action, detail: `${d.timestamp} · ${d.issue}`, run: () => navigate("decision"),
      })),
    ];
    if (!term) return items.slice(0, 9);
    return items.filter((i) => `${i.title} ${i.detail}`.toLowerCase().includes(term)).slice(0, 12);
  }, [q, alertsAll, summary, decisions, navigate, can, onOpenAlerts]);

  function choose(item) {
    onClose();
    item.run();
  }

  function onKey(e) {
    if (e.key === "Escape") onClose();
    if (e.key === "ArrowDown") { e.preventDefault(); setIndex((i) => Math.min(i + 1, results.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setIndex((i) => Math.max(i - 1, 0)); }
    if (e.key === "Enter" && results[index]) choose(results[index]);
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="overlay" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.div className="search-modal" role="dialog" aria-modal="true" aria-label="Search"
            initial={{ opacity: 0, y: -8, x: "-50%" }} animate={{ opacity: 1, y: 0, x: "-50%" }} exit={{ opacity: 0, y: -8, x: "-50%" }}>
            <input
              ref={inputRef}
              type="search"
              value={q}
              onChange={(e) => { setQ(e.target.value); setIndex(0); }}
              onKeyDown={onKey}
              placeholder="Search pages, alerts, resources, decisions…"
              aria-label="Search"
              aria-controls="search-results"
              aria-activedescendant={results[index] ? `sr-${index}` : undefined}
            />
            <ul className="search-results" id="search-results" role="listbox">
              {results.length === 0 && <li className="empty">No matches for “{q}”.</li>}
              {results.map((r, i) => (
                <li key={`${r.type}-${i}`} role="option" id={`sr-${i}`} aria-selected={i === index}>
                  <button aria-selected={i === index} onMouseEnter={() => setIndex(i)} onClick={() => choose(r)}>
                    <span className="row"><span className="pill">{r.type}</span><b style={{ fontSize: 13 }}>{r.title}</b></span>
                    <small>{r.detail}</small>
                  </button>
                </li>
              ))}
            </ul>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
