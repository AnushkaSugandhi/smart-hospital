import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { getAlerts, getConfig, getDashboardSummary, getHistory } from "../services/api";

const AppContext = createContext(null);
export const useApp = () => useContext(AppContext);

const ROLE_ORDER = ["Viewer", "Analyst", "Admin"];
export const hasRole = (user, minimum) =>
  ROLE_ORDER.indexOf(user?.role) >= ROLE_ORDER.indexOf(minimum || "Viewer");

const AUTO_REFRESH_MS = 60_000;

function parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [page, qs = ""] = raw.split("?");
  return { page: page || "overview", params: Object.fromEntries(new URLSearchParams(qs)) };
}

function readPref(key, fallback) {
  try { const v = localStorage.getItem(key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; }
}
function writePref(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

export function AppProvider({ user, onLogout, children }) {
  const [route, setRoute] = useState(parseHash);
  const [config, setConfig] = useState(null);
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [alertsAll, setAlertsAll] = useState([]);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastFetched, setLastFetched] = useState(null);
  const [autoRefresh, setAutoRefreshState] = useState(() => readPref("shdss_autorefresh", true));
  const [department, setDepartment] = useState("");
  const [rangeDays, setRangeDays] = useState(14);
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((page, params) => {
    const qs = params ? `?${new URLSearchParams(params)}` : "";
    window.location.hash = `/${page}${qs}`;
  }, []);

  const notify = useCallback((message, tone = "ok") => {
    setToast({ message, tone });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [s, h, a] = await Promise.all([
        getDashboardSummary(department || undefined),
        getHistory(department || undefined),
        getAlerts(true, department || undefined),
      ]);
      setSummary(s);
      setHistory(h);
      setAlertsAll(a);
      setLastFetched(new Date());
      setError("");
    } catch (e) {
      if (e.status !== 401) setError("We couldn't reach the hospital data service. It may be waking up — try again in a moment.");
    } finally {
      setRefreshing(false);
    }
  }, [department]);

  const reloadAlerts = useCallback(async () => {
    try { setAlertsAll(await getAlerts(true, department || undefined)); } catch {}
  }, [department]);

  useEffect(() => { getConfig().then(setConfig).catch(() => {}); }, []);
  useEffect(() => { refresh(); }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const id = setInterval(() => { if (!document.hidden) refresh(); }, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [autoRefresh, refresh]);

  const setAutoRefresh = (value) => { setAutoRefreshState(value); writePref("shdss_autorefresh", value); };

  const activeAlerts = useMemo(() => alertsAll.filter((a) => a.state === "active"), [alertsAll]);
  const rangedHistory = useMemo(() => history.slice(-rangeDays), [history, rangeDays]);

  const value = {
    user, onLogout, route, navigate, config, summary, history, rangedHistory, rangeDays, setRangeDays,
    alertsAll, activeAlerts, reloadAlerts, error, refreshing, refresh, lastFetched,
    autoRefresh, setAutoRefresh, autoRefreshMs: AUTO_REFRESH_MS, department, setDepartment,
    notify, toast, can: (role) => hasRole(user, role),
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
