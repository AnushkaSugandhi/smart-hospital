import React, { useEffect, useState } from "react";
import { Bell, LogOut, Menu, Moon, RefreshCw, Search, ShieldCheck, Sun } from "lucide-react";
import { useApp } from "../context/AppContext";
import InfoTip from "./InfoTip";

export function timeAgo(date, now = Date.now()) {
  if (!date) return "never";
  const secs = Math.max(0, Math.round((now - new Date(date).getTime()) / 1000));
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

function useNow(interval = 15000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), interval); return () => clearInterval(id); }, [interval]);
  return now;
}

export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") || "dark");
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("shdss_theme", theme); } catch {}
  }, [theme]);
  return [theme, setTheme];
}

export function PrivacyBadge() {
  return (
    <span className="row" style={{ gap: 4 }}>
      <span className="privacy-badge"><ShieldCheck size={13} aria-hidden="true" /> Data protected</span>
      <InfoTip label="How data is protected">
        Only aggregated operational numbers are stored. Names, phone numbers, emails and ID numbers in uploads are
        masked in previews and never saved. Access is role-based and every action is recorded in the audit log.
      </InfoTip>
    </span>
  );
}

export default function TopBar({ onMenu, onOpenAlerts, onOpenSearch }) {
  const {
    user, onLogout, summary, lastFetched, refreshing, refresh, autoRefresh, setAutoRefresh,
    activeAlerts, department, setDepartment,
  } = useApp();
  const [theme, setTheme] = useTheme();
  const now = useNow();
  const initials = (user.full_name || user.username).split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="icon-btn menu-btn" onClick={onMenu} aria-label="Open navigation"><Menu size={18} /></button>
        <div className="topbar-title">
          <span className="eyebrow">Operations command center</span>
          <strong>Vardhaman General Hospital</strong>
        </div>
      </div>

      <div className="topbar-actions">
        <button className="search-trigger" onClick={onOpenSearch} aria-label="Search (Ctrl+K)" data-tour="search">
          <Search size={15} aria-hidden="true" /> <span className="label">Search</span> <kbd>Ctrl K</kbd>
        </button>

        {summary?.departments?.length > 1 && (
          <label className="hide-sm">
            <span className="sr-only">Department</span>
            <select value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="">All departments</option>
              {summary.departments.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        )}

        <span className="live" data-tour="live" title={lastFetched ? lastFetched.toLocaleString() : ""}>
          <span className={`live-dot ${autoRefresh ? "" : "paused"}`} aria-hidden="true" />
          <span className="text">Updated {timeAgo(lastFetched, now)}</span>
        </span>
        <button className="icon-btn" onClick={refresh} disabled={refreshing} aria-label="Refresh data">
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />
        </button>
        <label className="toggle hide-sm" title="Refresh every minute">
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
          <span className="track" aria-hidden="true" /> Auto
        </label>

        <button className="icon-btn" onClick={onOpenAlerts} data-tour="alerts"
          aria-label={`Alerts, ${activeAlerts.length} active`}>
          <Bell size={16} />
          {activeAlerts.length > 0 && <span className="count">{activeAlerts.length}</span>}
        </button>

        <button className="icon-btn" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        <div className="user-chip">
          <span className="avatar" aria-hidden="true">{initials}</span>
          <span className="who">
            <strong>{user.full_name || user.username}</strong>
            <span className="role-pill">{user.role}</span>
          </span>
          <button className="icon-btn" style={{ width: 30, height: 30, border: 0 }} onClick={onLogout} aria-label="Sign out">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}
