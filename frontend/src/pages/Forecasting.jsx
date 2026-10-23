import React, { useEffect, useState } from "react";
import { Info, Table2 } from "lucide-react";
import { getForecast } from "../services/api";
import { useApp } from "../context/AppContext";
import PageHeader from "../components/PageHeader";
import ForecastChart, { ForecastTable } from "../components/ForecastChart";
import { Skeleton } from "../components/Skeleton";

const METRICS = [
  ["admissions", "Admissions"],
  ["emergency_cases", "Emergency cases"],
  ["bed_occupancy", "Bed occupancy"],
  ["icu_occupancy", "ICU occupancy"],
  ["doctor_workload", "Doctor workload"],
];

export default function Forecasting() {
  const { route, department, config, rangeDays, setRangeDays } = useApp();
  const [metric, setMetric] = useState(route.params.metric || "admissions");
  const [horizon, setHorizon] = useState(Number(route.params.horizon) || 7);
  const [forecast, setForecast] = useState(null);
  const [error, setError] = useState("");
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    if (route.params.metric) setMetric(route.params.metric);
    if (route.params.horizon) setHorizon(Number(route.params.horizon));
  }, [route.params.metric, route.params.horizon]);

  useEffect(() => {
    setForecast(null);
    setError("");
    getForecast(metric, horizon, department || undefined).then(setForecast).catch(() => setError("Forecast is unavailable right now."));
  }, [metric, horizon, department]);

  const isOccupancy = metric.endsWith("occupancy");
  const description = config?.metrics?.[metric]?.description;

  return (
    <div className="page">
      <PageHeader page="forecast" />
      <section className="card">
        <div className="row-wrap" style={{ marginBottom: 14 }}>
          <label className="field">Metric
            <select value={metric} onChange={(e) => setMetric(e.target.value)}>
              {METRICS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>
          </label>
          <label className="field">Forecast horizon
            <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
              <option value={3}>3 days</option><option value={7}>7 days</option><option value={14}>14 days</option>
            </select>
          </label>
          <label className="field">History shown
            <select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
              <option value={7}>7 days</option><option value={14}>14 days</option><option value={30}>30 days</option>
            </select>
          </label>
          <button className="btn btn-sm" style={{ alignSelf: "end" }} onClick={() => setShowTable((v) => !v)} aria-pressed={showTable}>
            <Table2 size={14} /> {showTable ? "Show chart" : "Show table"}
          </button>
        </div>
        {description && <p className="card-sub" style={{ marginTop: 0 }}>{description}</p>}
        {error ? <p>{error}</p> : !forecast ? <Skeleton height={320} /> : showTable ? (
          <ForecastTable forecast={forecast} />
        ) : (
          <ForecastChart forecast={forecast} historyDays={rangeDays}
            threshold={isOccupancy ? config?.status_bands?.red_above ?? 85 : undefined} />
        )}
        {forecast && (
          <div className="disclaimer" style={{ marginTop: 12 }}>
            <Info size={14} aria-hidden="true" />
            <span>
              Method: <b>{forecast.method.replace(/_/g, " ")}</b> · quality: {forecast.quality}.{" "}
              {forecast.method === "moving_average_fallback" && "Fewer than 14 days of history, so a flat average is shown. "}
              Forecasts support planning and are not clinical guidance.
            </span>
          </div>
        )}
      </section>
    </div>
  );
}
