import React, { useMemo } from "react";
import { useReducedMotion } from "framer-motion";
import useThemeColors from "../hooks/useThemeColors";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const RATIO_METRICS = new Set(["bed_occupancy", "icu_occupancy"]);

function addDays(iso, n) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
const short = (iso) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });

function ChartTip({ active, payload, label, unit }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <b>{label}</b>
      {payload.filter((p) => p.value != null).map((p) => (
        <div key={p.dataKey}><i style={{ background: p.stroke }} />{p.name}: <b>{p.value}{unit}</b></div>
      ))}
    </div>
  );
}

// Historical (solid, series 1) vs forecast (dashed, series 2) on one axis.
export default function ForecastChart({ forecast, historyDays = 14, height = 320, threshold, compact = false }) {
  const reduce = useReducedMotion();
  const c = useThemeColors();
  const ratio = RATIO_METRICS.has(forecast?.metric);
  const unit = ratio ? "%" : "";
  const scale = (v) => (v == null ? null : ratio ? Math.round(v * 1000) / 10 : Math.round(v * 100) / 100);

  const data = useMemo(() => {
    if (!forecast) return [];
    const hist = forecast.historical.slice(-historyDays);
    const dates = (forecast.dates || []).slice(-historyDays);
    const lastDate = dates[dates.length - 1];
    const rows = hist.map((v, i) => ({ day: dates[i] ? short(dates[i]) : `H-${hist.length - i}`, historical: scale(v), forecast: null }));
    // Connect the forecast to the last actual point so the line is continuous.
    if (rows.length) rows[rows.length - 1].forecast = rows[rows.length - 1].historical;
    forecast.forecast.forEach((v, i) => {
      rows.push({ day: lastDate ? short(addDays(lastDate, i + 1)) : `D+${i + 1}`, historical: null, forecast: scale(v) });
    });
    return rows;
  }, [forecast, historyDays]);

  return (
    <div>
      <div className="legend" aria-hidden="true" style={{ marginBottom: 8 }}>
        <span><i style={{ background: "var(--series-1)" }} />Actual</span>
        <span style={{ color: "var(--series-2)" }}><i className="dashed" style={{ background: "var(--series-2)" }} /><span style={{ color: "var(--text-2)" }}>Forecast</span></span>
        {threshold != null && <span><i style={{ background: "var(--muted)" }} />Red threshold ({threshold}%)</span>}
      </div>
      <div className="chart-box" style={{ height }} role="img"
        aria-label={`${forecast?.metric} actual for ${historyDays} days and ${forecast?.horizon}-day forecast`}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis dataKey="day" stroke={c.axis} tick={{ fill: c.muted, fontSize: 11 }} tickLine={false} minTickGap={18} />
            <YAxis stroke={c.axis} tick={{ fill: c.muted, fontSize: 11 }} tickLine={false} axisLine={false}
              domain={["auto", "auto"]} unit={unit} tickFormatter={(v) => +Number(v).toFixed(ratio ? 0 : 1)} allowDecimals={!ratio} width={compact ? 46 : 52} />
            <Tooltip content={<ChartTip unit={unit} />} cursor={{ stroke: c.axis }} />
            {threshold != null && <ReferenceLine y={threshold} stroke={c.muted} />}
            <Line type="monotone" dataKey="historical" name="Actual" stroke={c["series-1"]} strokeWidth={2}
              dot={false} activeDot={{ r: 4, stroke: c["surface-solid"], strokeWidth: 2 }} isAnimationActive={!reduce} animationDuration={1200} />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke={c["series-2"]} strokeWidth={2} strokeDasharray="5 4"
              dot={{ r: 3, fill: c["series-2"], stroke: c["surface-solid"], strokeWidth: 2 }}
              isAnimationActive={!reduce} animationBegin={600} animationDuration={900} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ForecastTable({ forecast }) {
  const ratio = RATIO_METRICS.has(forecast.metric);
  const lastDate = forecast.dates?.[forecast.dates.length - 1];
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Forecast values</caption>
        <thead><tr><th>Day</th><th>Forecast</th></tr></thead>
        <tbody>
          {forecast.forecast.map((v, i) => (
            <tr key={i}>
              <td>{lastDate ? addDays(lastDate, i + 1) : `D+${i + 1}`}</td>
              <td className="num">{ratio ? `${(v * 100).toFixed(1)}%` : v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
