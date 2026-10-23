import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Info, Play, RotateCcw } from "lucide-react";
import { runSimulation } from "../services/api";
import { useApp } from "../context/AppContext";
import { statusForPct } from "../config/metrics";
import PageHeader from "../components/PageHeader";
import RiskGauge from "../components/RiskGauge";
import StatusBadge from "../components/StatusBadge";

export const SIM_PARAMS = [
  ["admissions_change_pct", "Admissions", -20, 60],
  ["emergency_cases_change_pct", "Emergency cases", -30, 60],
  ["available_beds_change_pct", "Available beds", -20, 30],
  ["icu_capacity_change_pct", "ICU capacity", -20, 30],
  ["doctor_availability_change_pct", "Doctor availability", -30, 40],
  ["staff_availability_change_pct", "Staff availability", -30, 40],
];
const ZERO = Object.fromEntries(SIM_PARAMS.map(([k]) => [k, 0]));

const ROWS = [
  ["bed_occupancy_pct", "Bed occupancy", "%", true],
  ["icu_occupancy_pct", "ICU occupancy", "%", true],
  ["doctor_workload", "Patients per doctor", "", false],
  ["staff_workload", "Patients per staff", "", false],
  ["emergency_pressure_pct", "Emergency pressure", "%", true],
];

export default function Simulator() {
  const { route, config } = useApp();
  const [params, setParams] = useState(() => ({ ...ZERO, admissions_change_pct: 20 }));
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run(p = params) {
    setBusy(true);
    try { setResult(await runSimulation({ name: "What-if scenario", department: "Emergency", ...p })); }
    finally { setBusy(false); }
  }

  // Prefill from links such as "Run in Simulator" in the chatbot.
  useEffect(() => {
    const incoming = Object.fromEntries(SIM_PARAMS.filter(([k]) => route.params[k] != null).map(([k]) => [k, Number(route.params[k])]));
    if (Object.keys(incoming).length) {
      const next = { ...ZERO, ...incoming };
      setParams(next);
      run(next);
    } else {
      run();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.params]);

  const bands = config?.status_bands;
  const levels = config?.risk_levels || [];

  return (
    <div className="page">
      <PageHeader page="whatif" />
      <div className="grid grid-hero">
        <section className="card" aria-labelledby="sim-controls">
          <div className="card-title" id="sim-controls"><Play size={17} aria-hidden="true" /> Scenario</div>
          <div className="stack">
            {SIM_PARAMS.map(([key, label, min, max]) => (
              <div className="slider-row" key={key}>
                <div className="spread">
                  <label htmlFor={key}>{label}</label>
                  <b>{params[key] > 0 ? "+" : ""}{params[key]}%</b>
                </div>
                <input id={key} type="range" min={min} max={max} step="5" value={params[key]}
                  onChange={(e) => setParams({ ...params, [key]: Number(e.target.value) })} />
              </div>
            ))}
          </div>
          <div className="row-wrap" style={{ marginTop: 12 }}>
            <button className="btn btn-primary" onClick={() => run()} disabled={busy}><Play size={14} /> {busy ? "Simulating…" : "Run scenario"}</button>
            <button className="btn" onClick={() => { setParams(ZERO); run(ZERO); }}><RotateCcw size={14} /> Reset</button>
          </div>
        </section>

        <section className="card" aria-live="polite" aria-labelledby="sim-result">
          <div className="card-title" id="sim-result">Result</div>
          {result && (
            <>
              <div className="compare-grid">
                <div className="inset">
                  <span className="eyebrow">Today</span>
                  <RiskGauge compact levels={levels} risk={{ score: result.baseline.risk_score, level: result.baseline.risk_level,
                    level_label: result.baseline.risk_level[0].toUpperCase() + result.baseline.risk_level.slice(1), breakdown: [] }} />
                </div>
                <motion.div className="inset" key={result.simulated.risk_score} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }}>
                  <span className="eyebrow">Scenario</span>
                  <RiskGauge compact levels={levels} risk={{ score: result.simulated.risk_score, level: result.simulated.risk_level,
                    level_label: result.simulated.risk_level_label, breakdown: result.simulated.risk_breakdown }} />
                </motion.div>
              </div>
              <div style={{ marginTop: 12 }}>
                <div className="compare-row muted" style={{ fontSize: 11, fontWeight: 700 }}>
                  <span>Measure</span><span>Today</span><span /><span>Scenario</span>
                </div>
                {ROWS.map(([key, label, unit, pct]) => {
                  const before = result.baseline[key];
                  const after = result.simulated[key];
                  return (
                    <div className="compare-row" key={key}>
                      <span>{label}</span>
                      <span className="num">{Number(before).toFixed(1)}{unit}</span>
                      <ArrowRight size={14} aria-hidden="true" />
                      <span className="row num" style={{ justifyContent: "flex-end" }}>
                        <b>{Number(after).toFixed(1)}{unit}</b>
                        {pct && <StatusBadge status={statusForPct(after, bands)} />}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
          <div className="disclaimer" style={{ marginTop: 10 }}><Info size={14} aria-hidden="true" />
            Aggregate estimate using the same risk formula as the dashboard. It does not change any hospital resources.
          </div>
        </section>
      </div>
    </div>
  );
}
