import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Lightbulb, Sparkles, X } from "lucide-react";
import { decideNextAction, getNextActions } from "../services/api";
import { useApp } from "../context/AppContext";
import { EmptyState, Skeleton } from "./Skeleton";

// "What should I do now?" — top 3 recommendations with Why, Impact, Approve/Dismiss.
export default function NextActions() {
  const { department, can, notify, summary, navigate } = useApp();
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(() => {
    getNextActions(department || undefined).then(setItems).catch(() => setItems([]));
  }, [department]);
  useEffect(load, [load, summary?.generated_at]);

  async function decide(item, decision) {
    setBusy(item.id);
    try {
      await decideNextAction(item.id, decision);
      notify(decision === "approve" ? "Approved and logged to Decision Center" : "Dismissed and logged to Decision Center");
      setItems((list) => list.filter((i) => i.id !== item.id));
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="card" data-tour="next-actions" aria-labelledby="next-title">
      <div className="card-title" id="next-title"><Sparkles size={17} aria-hidden="true" /> What should I do now?</div>
      <p className="card-sub">Top actions ranked by how much each factor adds to risk. Impact is estimated with the What-if Simulator.</p>
      {items == null ? (
        <div className="stack"><Skeleton height={90} /><Skeleton height={90} /></div>
      ) : items.length === 0 ? (
        <EmptyState icon={Lightbulb} title="No urgent actions">All risk factors are in the green band. Check back after the next update.</EmptyState>
      ) : (
        <div className="stack">
          <AnimatePresence initial={false}>
            {items.map((item, i) => (
              <motion.div key={item.id} className="next-action" layout
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 30 }}>
                <h4><span className="idx">{i + 1}</span>{item.title}</h4>
                <dl>
                  <dt>Why</dt><dd>{item.why}</dd>
                  <dt>Impact</dt><dd><b style={{ color: "var(--text)" }}>{item.impact}</b></dd>
                </dl>
                <div className="row-wrap">
                  {can("Analyst") ? (
                    <>
                      <button className="btn btn-sm btn-primary" disabled={busy === item.id} onClick={() => decide(item, "approve")}>
                        <Check size={14} /> Approve
                      </button>
                      <button className="btn btn-sm" disabled={busy === item.id} onClick={() => decide(item, "dismiss")}>
                        <X size={14} /> Dismiss
                      </button>
                    </>
                  ) : <small>Analysts and Admins can approve actions.</small>}
                  <button className="btn btn-sm btn-ghost" onClick={() => navigate("whatif", item.scenario)}>Try in simulator</button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </section>
  );
}
