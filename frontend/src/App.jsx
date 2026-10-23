import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, HelpCircle, RefreshCw } from "lucide-react";
import { clearSession, getStoredUser, onUnauthorized } from "./services/api";
import { AppProvider, useApp } from "./context/AppContext";
import { PAGE_BY_KEY } from "./config/pages";
import useRipple from "./hooks/useRipple";
import EcgBackground from "./components/EcgBackground";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import AlertBanner from "./components/AlertBanner";
import AlertsPanel from "./components/AlertsPanel";
import GlobalSearch from "./components/GlobalSearch";
import Tour from "./components/Tour";
import { OverviewSkeleton } from "./components/Skeleton";
import LoginPage from "./pages/LoginPage";
import Overview from "./pages/Overview";
import Hindsight from "./pages/Hindsight";
import Forecasting from "./pages/Forecasting";
import CascadeFlow from "./pages/CascadeFlow";
import Simulator from "./pages/Simulator";
import DecisionCenter from "./pages/DecisionCenter";
import DataUpload from "./pages/DataUpload";
import AuditLog from "./pages/AuditLog";
import AskAI from "./pages/AskAI";
import { ChatProvider } from "./chat/ChatContext";
import ChatPanel from "./chat/ChatPanel";

const PAGE_COMPONENTS = {
  overview: Overview,
  hindsight: Hindsight,
  forecast: Forecasting,
  cascade: CascadeFlow,
  whatif: Simulator,
  decision: DecisionCenter,
  upload: DataUpload,
  audit: AuditLog,
  ask: AskAI,
};

function Shell() {
  const { route, navigate, summary, error, refresh, refreshing, can, toast } = useApp();
  const [menuOpen, setMenuOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [tourRequested, setTourRequested] = useState(false);
  useRipple();

  const openAlerts = useCallback(() => setAlertsOpen(true), []);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearchOpen(true); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Unknown pages, or pages above the user's role, fall back to Overview.
  const meta = PAGE_BY_KEY[route.page];
  const pageKey = meta && can(meta.minRole) ? route.page : "overview";
  useEffect(() => { if (pageKey !== route.page) navigate("overview"); }, [pageKey, route.page, navigate]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [pageKey]);

  const Page = PAGE_COMPONENTS[pageKey];

  return (
    <div className="shell">
      <a href="#main" className="skip-link">Skip to content</a>
      <EcgBackground />
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <main className="main" id="main">
        <TopBar onMenu={() => setMenuOpen(true)} onOpenAlerts={openAlerts} onOpenSearch={() => setSearchOpen(true)} />
        <AlertBanner onOpen={openAlerts} />

        {error && !summary ? (
          <div className="card empty" role="alert">
            <AlertCircle size={30} aria-hidden="true" />
            <strong>Data service unavailable</strong>
            <span>{error}</span>
            <button className="btn btn-primary" onClick={refresh} disabled={refreshing}>
              <RefreshCw size={14} className={refreshing ? "spin" : ""} /> Try again
            </button>
          </div>
        ) : !summary ? (
          <OverviewSkeleton />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div key={pageKey} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.22 }}>
              <Page onOpenAlerts={openAlerts} />
            </motion.div>
          </AnimatePresence>
        )}

        {summary && pageKey === "overview" && (
          <button className="btn btn-ghost btn-sm" style={{ marginTop: 18 }} onClick={() => setTourRequested(true)}>
            <HelpCircle size={14} /> Take the 1-minute tour
          </button>
        )}
      </main>

      <AlertsPanel open={alertsOpen} onClose={() => setAlertsOpen(false)} />
      <ChatPanel />
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} onOpenAlerts={openAlerts} />
      {summary && pageKey === "overview" && <Tour forceOpen={tourRequested} onDone={() => setTourRequested(false)} />}

      <AnimatePresence>
        {toast && (
          <motion.div className="toast" role="status" initial={{ opacity: 0, y: 12, x: "-50%" }} animate={{ opacity: 1, y: 0, x: "-50%" }} exit={{ opacity: 0, y: 12, x: "-50%" }}>
            {toast.tone === "error"
              ? <AlertCircle size={16} style={{ color: "var(--status-critical)" }} aria-hidden="true" />
              : <CheckCircle2 size={16} style={{ color: "var(--status-good)" }} aria-hidden="true" />}
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(getStoredUser());
  useEffect(() => onUnauthorized(() => setUser(null)), []);
  if (!user) return <LoginPage onLogin={setUser} />;
  return (
    <AppProvider user={user} onLogout={() => { clearSession(); setUser(null); }}>
      <ChatProvider>
        <Shell />
      </ChatProvider>
    </AppProvider>
  );
}
