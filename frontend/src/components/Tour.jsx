import React, { useEffect, useLayoutEffect, useState } from "react";

const STEPS = [
  { target: "risk", title: "Start with the risk score", body: "One number for overall pressure (0–100), with the factors that drive it. Hover the ⓘ for the formula." },
  { target: "kpis", title: "Watch the trends", body: "Each card shows today’s value, its status, a 14-day sparkline and the change vs the previous day." },
  { target: "alerts", title: "Alerts and predictions", body: "The bell counts active alerts, including predictions like “ICU likely full in ~6 hours”. Acknowledge or snooze them." },
  { target: "next-actions", title: "Decide what to do", body: "“What should I do now?” lists the top actions with why and estimated impact. Approving logs it to the Decision Center." },
];
const KEY = "shdss_tour_done";

// First-time 4-step tour. Highlights a [data-tour] element and explains it.
export default function Tour({ forceOpen = false, onDone }) {
  const [step, setStep] = useState(0);
  const [open, setOpen] = useState(() => {
    try { return forceOpen || !localStorage.getItem(KEY); } catch { return forceOpen; }
  });
  const [rect, setRect] = useState(null);

  useEffect(() => { if (forceOpen) { setStep(0); setOpen(true); } }, [forceOpen]);

  useLayoutEffect(() => {
    if (!open) return undefined;
    const measure = () => {
      const el = document.querySelector(`[data-tour="${STEPS[step].target}"]`);
      if (!el) { setRect(null); return; }
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
      setRect(el.getBoundingClientRect());
    };
    const id = setTimeout(measure, 350);
    window.addEventListener("resize", measure);
    return () => { clearTimeout(id); window.removeEventListener("resize", measure); };
  }, [open, step]);

  function finish() {
    try { localStorage.setItem(KEY, "1"); } catch {}
    setOpen(false);
    onDone?.();
  }

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!open) return null;
  const s = STEPS[step];
  const pad = 6;
  const popTop = rect ? Math.min(rect.bottom + 12, window.innerHeight - 190) : window.innerHeight / 2 - 90;
  const popLeft = rect ? Math.min(Math.max(rect.left, 16), window.innerWidth - 336) : window.innerWidth / 2 - 160;

  return (
    <>
      {rect && (
        <div className="tour-spot" style={{ top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2 }} />
      )}
      <div className="tour-pop" role="dialog" aria-modal="true" aria-labelledby="tour-title" style={{ top: popTop, left: popLeft }}>
        <span className="eyebrow">Step {step + 1} of {STEPS.length}</span>
        <h3 id="tour-title">{s.title}</h3>
        <p style={{ fontSize: 13 }}>{s.body}</p>
        <div className="spread" style={{ marginTop: 10 }}>
          <button className="btn btn-ghost btn-sm" onClick={finish}>Skip tour</button>
          <div className="row">
            {step > 0 && <button className="btn btn-sm" onClick={() => setStep(step - 1)}>Back</button>}
            <button className="btn btn-sm btn-primary" autoFocus
              onClick={() => (step === STEPS.length - 1 ? finish() : setStep(step + 1))}>
              {step === STEPS.length - 1 ? "Got it" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
