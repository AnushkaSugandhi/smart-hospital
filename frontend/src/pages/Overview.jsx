import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, BellRing, CheckCircle2, ClipboardList, Gauge, Package } from "lucide-react";
import { getDecisions, getForecast } from "../services/api";
import { useApp } from "../context/AppContext";
import { KPI_CARDS } from "../config/metrics";
import PageHeader from "../components/PageHeader";
import RiskGauge from "../components/RiskGauge";
import KpiCard from "../components/KpiCard";
import AlertCard from "../components/AlertCard";
import ResourceCard from "../components/ResourceCard";
import NextActions from "../components/NextActions";
import ForecastChart from "../components/ForecastChart";
import { EmptyState, Skeleton } from "../components/Skeleton";
import { PrivacyBadge } from "../components/TopBar";

const short = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });

export default function Overview({ onOpenAlerts }) {
  const { summary, rangedHistory, rangeDays, setRangeDays, config, activeAlerts, navigate, department } = useApp();
  const [forecast, setForecast] = useState(null);
  const [decisions, setDecisions] = useState(null);

  useEffect(() => {
    getForecast("icu_occupancy", 7, department || undefined).then(setForecast).catch(() => setForecast(null));
    getDecisions().then((d) => setDecisions(d.slice(0, 5))).catch(() => setDecisions([]));
  }, [department, summary?.generated_at]);

  const d = summary;
  const red = config?.status_bands?.red_above ?? 85;

  return (
    <div className="page">
      <PageHeader page="overview">
        <PrivacyBadge />
        <label className="row" style={{ fontSize: 12, color: "var(--text-2)" }}>
          Trend window
          <select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </label>
      </PageHeader>

      {/* 1. Risk gauge + top alerts */}
      <div className="grid grid-hero">
        <motion.section className="card" data-tour="risk" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          aria-labelledby="risk-title">
          <div className="card-title" id="risk-title"><Gauge size={17} aria-hidden="true" /> Resource risk</div>
          <p className="card-sub">Data for {short(d.date)} · {d.department} · top driver: {d.risk.top_driver}</p>
          <RiskGauge risk={d.risk} levels={config?.risk_levels || []} />
        </motion.section>

        <motion.section className="card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0, transition: { delay: 0.08 } }}
          aria-labelledby="top-alerts-title">
          <div className="spread" style={{ marginBottom: 12 }}>
            <div className="card-title" id="top-alerts-title" style={{ margin: 0 }}><BellRing size={17} aria-hidden="true" /> Top alerts</div>
            <button className="btn btn-sm" onClick={onOpenAlerts}>All alerts ({activeAlerts.length}) <ArrowRight size={14} /></button>
          </div>
          {activeAlerts.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="No active alerts">Every monitored resource is within safe limits.</EmptyState>
          ) : (
            <div className="stack">
              {activeAlerts.slice(0, 3).map((a) => <AlertCard key={a.id} alert={a} compact />)}
            </div>
          )}
        </motion.section>
      </div>

      {/* 2. KPI cards with trends */}
      <section aria-label="Key indicators" data-tour="kpis" className="grid grid-4">
        {KPI_CARDS.map((k, i) => {
          const block = d[k.block];
          return (
            <KpiCard
              key={k.key}
              index={i}
              title={k.title}
              value={k.value(d)}
              decimals={k.decimals}
              suffix={k.suffix}
              unit={k.unit}
              subtitle={k.subtitle(d)}
              status={block.status}
              info={<>{config?.metrics?.[k.key]?.description} <span className="tip-line"><b>Formula:</b> {block.formula}</span></>}
              trend={d.trends?.[k.key]}
              series={rangedHistory.map((h) => ({ label: short(h.date), value: h[k.history] == null ? null : +(h[k.history] * k.scale).toFixed(1) }))}
              format={(v) => `${v}${k.suffix || ""}`}
            />
          );
        })}
      </section>

      {/* 3. Forecast preview + what to do now */}
      <div className="grid grid-2">
        <section className="card" aria-labelledby="fc-title">
          <div className="spread" style={{ marginBottom: 6 }}>
            <div className="card-title" id="fc-title" style={{ margin: 0 }}><BarChart3 size={17} aria-hidden="true" /> ICU occupancy forecast</div>
            <button className="btn btn-sm" onClick={() => navigate("forecast", { metric: "icu_occupancy" })}>Open Forecasting <ArrowRight size={14} /></button>
          </div>
          <p className="card-sub" style={{ marginTop: 0 }}>Next 7 days{forecast ? ` · ${forecast.method.replace(/_/g, " ")}` : ""}</p>
          {forecast ? <ForecastChart forecast={forecast} historyDays={rangeDays} height={330} threshold={red} compact />
            : <Skeleton height={230} />}
        </section>
        <NextActions />
      </div>

      {/* 4. Resource cards */}
      <section aria-labelledby="res-title">
        <div className="card-title" id="res-title"><Package size={17} aria-hidden="true" /> Critical resources</div>
        <div className="grid grid-auto">
          {d.resources.map((r, i) => <ResourceCard key={r.key} card={r} index={i} />)}
        </div>
      </section>

      {/* 5. Recent decisions */}
      <section className="card" aria-labelledby="dec-title">
        <div className="spread" style={{ marginBottom: 10 }}>
          <div className="card-title" id="dec-title" style={{ margin: 0 }}><ClipboardList size={17} aria-hidden="true" /> Recent decisions</div>
          <button className="btn btn-sm" onClick={() => navigate("decision")}>Decision Center <ArrowRight size={14} /></button>
        </div>
        {decisions == null ? <Skeleton height={120} /> : decisions.length === 0 ? (
          <EmptyState icon={ClipboardList} title="No decisions recorded yet">Approve a recommendation above to create the first one.</EmptyState>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>When</th><th>Action</th><th>Status</th><th>By</th></tr></thead>
              <tbody>
                {decisions.map((x) => (
                  <tr key={x.id}>
                    <td className="num">{x.timestamp}</td>
                    <td style={{ color: "var(--text)" }}>{x.administrator_action}</td>
                    <td><span className="pill">{x.outcome}</span></td>
                    <td>{x.recorded_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
