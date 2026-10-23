import React, { useState } from "react";
import { motion } from "framer-motion";
import { Lock, ShieldCheck, User } from "lucide-react";
import { login } from "../services/api";
import EcgBackground from "../components/EcgBackground";

const DEMO = [
  ["admin", "admin123", "Admin — everything, incl. rollback & audit"],
  ["analyst", "analyst123", "Analyst — upload, decide, acknowledge"],
  ["viewer", "viewer123", "Viewer — read-only"],
];

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await login(username, password);
      onLogin(result.user);
    } catch (err) {
      setError(err.status === 401 ? "Invalid username or password." : "Cannot reach the server. Please try again shortly.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <EcgBackground />
      <motion.form
        className="glass login-card"
        onSubmit={submit}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        aria-labelledby="login-title"
      >
        <div className="brand login-brand">
          <div className="brand-mark">VGH</div>
          <div>
            <strong>Vardhaman General Hospital</strong>
            <span>Smart Hospital Decision Support</span>
          </div>
        </div>
        <h1 id="login-title">Sign in</h1>
        <p className="muted">Use your hospital account. Access is based on your role.</p>

        <label className="field">
          <span>Username</span>
          <div className="input-icon">
            <User size={15} aria-hidden="true" />
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </div>
        </label>
        <label className="field">
          <span>Password</span>
          <div className="input-icon">
            <Lock size={15} aria-hidden="true" />
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password" required />
          </div>
        </label>

        {error && <div className="form-error" role="alert">{error}</div>}

        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <details className="demo-accounts">
          <summary>Demo accounts</summary>
          <ul>
            {DEMO.map(([u, p, label]) => (
              <li key={u}>
                <button type="button" className="link-btn" onClick={() => { setUsername(u); setPassword(p); }}>
                  {u} / {p}
                </button>
                <small>{label}</small>
              </li>
            ))}
          </ul>
        </details>

        <div className="privacy-note">
          <ShieldCheck size={14} aria-hidden="true" /> Data protected · personal fields are never stored
        </div>
      </motion.form>
    </div>
  );
}
