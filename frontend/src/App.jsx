import React from "react";
import DataUpload from "./pages/DataUpload";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  CheckCircle,
  Clock,
  Database,
  GitBranch,
  History,
  LayoutDashboard,
  Play,
  RefreshCw,
  ShieldAlert,
  Sliders,
  UserCheck,
  Users,
} from "lucide-react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  analyzeCascade,
  getDashboardSummary,
  getDecisions,
  getForecast,
  getHistory,
  recordDecision,
  runSimulation,
  searchHindsight,
} from "./services/api";

const nav = [
  ["Overview", "overview", LayoutDashboard],
  ["Hindsight", "hindsight", History],
  ["Forecasting", "forecast", BarChart3],
  ["CascadeFlow", "cascade", GitBranch],
  ["What-if Simulator", "whatif", Play],
  ["Decision Center", "decision", ShieldAlert],
  ["Data Upload", "upload", Activity],
];

function Kpi({ title, value, subtitle, tone = "" }) {
  return (
    <div className="card kpi">
      <div className="muted">{title}</div>
      <div className={`kpi-value ${tone}`}>{value}</div>
      <div className="muted">{subtitle}</div>
    </div>
  );
}

function App() {
  const [page, setPage] = useState("overview");
  const [dashboard, setDashboard] = useState(null);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [hindsight, setHindsight] = useState(null);
  const [cascade, setCascade] = useState(null);
  const [simulation, setSimulation] = useState(null);
  const [decisions, setDecisions] = useState([]);

  // Simulation parameters
  const [admissionsChange, setAdmissionsChange] = useState(20);
  const [emergencyChange, setEmergencyChange] = useState(0);
  const [doctorChange, setDoctorChange] = useState(0);

  // Decision state
  const [customAction, setCustomAction] = useState(
    "Review step-down beds and reassign 2 float doctors."
  );
  const [decisionDepartment, setDecisionDepartment] = useState("Emergency");
  const [decisionStatus, setDecisionStatus] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // App & auth state
  const [metric, setMetric] = useState("admissions");
  const [error, setError] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [currentUser, setCurrentUser] = useState({
    username: "admin",
    role: "Chief Operations Officer",
    full_name: "Dr. Sarah Chen",
  });

  async function loadDashboard() {
    try {
      setIsRefreshing(true);
      setError("");
      const [d, h] = await Promise.all([
        getDashboardSummary(),
        getHistory(),
      ]);
      setDashboard(d);
      setHistory(h);
    } catch (e) {
      setError(
        "Backend is not reachable. Start FastAPI with: uvicorn app.main:app --reload"
      );
    } finally {
      setIsRefreshing(false);
    }
  }

  async function loadDecisionsList() {
    try {
      const data = await getDecisions();
      setDecisions(data);
    } catch (e) {
      console.error("Could not fetch decisions", e);
    }
  }

  useEffect(() => {
    loadDashboard();
    loadDecisionsList();
  }, []);

  useEffect(() => {
    if (page === "forecast") {
      getForecast(metric, 7).then(setForecast).catch(() => {});
    }
    if (page === "hindsight") {
      searchHindsight().then(setHindsight).catch(() => {});
    }
    if (page === "decision") {
      loadDecisionsList();
    }
  }, [page, metric]);

  const chartData = useMemo(() => {
    if (!forecast) return [];
    const hist = forecast.historical.slice(-14).map((value, i) => ({
      day: `H-${13 - i}`,
      historical: value,
      forecast: null,
    }));
    const future = forecast.forecast.map((value, i) => ({
      day: `D+${i + 1}`,
      historical: null,
      forecast: value,
    }));
    return [...hist, ...future];
  }, [forecast]);

  async function handleCascade() {
    const result = await analyzeCascade({
      driver: "admissions",
      change_pct: Number(admissionsChange),
      department: "Emergency",
    });
    setCascade(result);
    setPage("cascade");
  }

  async function handleSimulation() {
    const result = await runSimulation({
      name: "Custom Multi-factor Simulation",
      department: "Emergency",
      admissions_change_pct: Number(admissionsChange),
      emergency_cases_change_pct: Number(emergencyChange),
      available_beds_change_pct: 0,
      icu_capacity_change_pct: 0,
      doctor_availability_change_pct: Number(doctorChange),
      staff_availability_change_pct: 0,
    });
    setSimulation(result);
  }

  async function saveDecision() {
    if (!customAction.trim()) return;
    setIsSubmittingDecision(true);
    try {
      await recordDecision({
        issue: "Elevated bed and emergency capacity pressure",
        recommendation:
          "Review bed allocation, compatible doctor shift distribution, and step-down capacity.",
        administrator_action: customAction,
        outcome: "pending",
        outcome_details: "Monitoring 48h resolution metrics.",
        department: decisionDepartment,
        recorded_by: `${currentUser.full_name} (${currentUser.role})`,
      });
      setDecisionStatus("Decision permanently recorded in database.");
      loadDecisionsList();
      setTimeout(() => setDecisionStatus(""), 4000);
    } catch (err) {
      setDecisionStatus("Saved in session mode.");
    } finally {
      setIsSubmittingDecision(false);
    }
  }

  if (error) {
    return (
      <div className="center-page">
        <div className="card error-card">
          <h2>Backend Connection Required</h2>
          <p>{error}</p>
          <code>cd backend</code>
          <code>.venv\Scripts\Activate.ps1</code>
          <code>uvicorn app.main:app --reload</code>
          <button style={{ marginTop: 15 }} onClick={loadDashboard}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="center-page">
        <div style={{ textAlign: "center" }}>
          <RefreshCw className="spin" size={32} color="#5fe0d3" />
          <p style={{ marginTop: 12 }}>Loading Vardhaman General Hospital Command Center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">VGH</div>
          <div>
            <strong>Operations</strong>
            <span>Intelligence System</span>
          </div>
        </div>

        <div className="side-label">COMMAND CENTER</div>
        {nav.map(([label, key, Icon]) => (
          <button
            className={`nav-button ${page === key ? "active" : ""}`}
            onClick={() => setPage(key)}
            key={key}
          >
            <Icon size={17} />
            {label}
          </button>
        ))}

        <div className="side-note">
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Database size={14} color="#5fe0d3" />
            <strong style={{ margin: 0 }}>Operational DB</strong>
          </div>
          <span>Active snapshot repository connected.</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">HOSPITAL OPERATIONS COMMAND CENTER</div>
            <h1>Vardhaman General Hospital</h1>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-btn"
              title="Refresh data"
              onClick={loadDashboard}
              disabled={isRefreshing}
            >
              <RefreshCw size={14} className={isRefreshing ? "spin" : ""} />
              {isRefreshing ? "Updating..." : "Refresh"}
            </button>
            <div className="admin">
              <UserCheck size={16} color="#5fe0d3" />
              <div>
                <strong>{currentUser.full_name}</strong>
                <small style={{ display: "block", color: "#8da1b6" }}>{currentUser.role}</small>
              </div>
            </div>
          </div>
        </header>

        <section className="hero">
          <div>
            <div className="eyebrow">OBSERVE → REMEMBER → PREDICT → ANALYZE → DECIDE</div>
            <h2>Operational decision support for hospital administrators.</h2>
            <p>
              Monitor resources, leverage historical memory, forecast demand,
              simulate scenarios, and record auditable executive decisions.
            </p>
          </div>
          <div className="risk">
            <span>RESOURCE RISK</span>
            <strong>{dashboard.risk.score}</strong>
            <small>{dashboard.risk.level.toUpperCase()}</small>
          </div>
        </section>

        <section className="kpi-grid">
          <Kpi
            title="Bed occupancy"
            value={`${dashboard.beds.occupancy_pct}%`}
            subtitle={`${dashboard.beds.available} available of ${dashboard.beds.total}`}
            tone="critical"
          />
          <Kpi
            title="ICU occupancy"
            value={`${dashboard.icu.occupancy_pct}%`}
            subtitle={`${dashboard.icu.available} available of ${dashboard.icu.total}`}
            tone="warning"
          />
          <Kpi
            title="Doctor workload"
            value={dashboard.doctors.average_patients_per_doctor}
            subtitle={`${dashboard.doctors.overloaded} flagged overloaded`}
            tone="warning"
          />
          <Kpi
            title="Emergency cases"
            value={dashboard.emergency.active_cases}
            subtitle={`${dashboard.emergency.pressure_pct}% pressure`}
            tone="critical"
          />
        </section>

        {page === "overview" && (
          <>
            <div className="grid-2">
              <section className="card">
                <div className="section-title">
                  <ShieldAlert size={18} /> What requires attention?
                </div>
                {dashboard.alerts.map((a) => (
                  <div className="alert" key={a.id}>
                    <div className="alert-top">
                      <span>{a.severity.toUpperCase()}</span>
                      <strong>{a.resource_type}</strong>
                    </div>
                    <p>{a.reason}</p>
                    <small>{a.suggested_action}</small>
                  </div>
                ))}
              </section>

              <section className="card">
                <div className="section-title">
                  <History size={18} /> Hindsight Memory
                </div>
                <div className="memory">
                  <span>Most similar historical event</span>
                  <strong>
                    {dashboard.hindsight.date} · {dashboard.hindsight.similarity_score}% similar
                  </strong>
                  <p>{dashboard.hindsight.situation}</p>
                  <small>
                    <b>Previous action:</b> {dashboard.hindsight.previous_action}
                  </small>
                  <p>
                    <b>Outcome:</b> {dashboard.hindsight.outcome}
                  </p>
                  <button onClick={() => setPage("hindsight")}>
                    Open Hindsight Explorer
                  </button>
                </div>
              </section>
            </div>

            <div className="grid-2">
              <section className="card">
                <div className="section-title">
                  <GitBranch size={18} /> CascadeFlow Dynamics
                </div>
                <div className="cascade-preview">
                  Admissions <b>↓</b> Bed demand <b>↓</b> ICU pressure{" "}
                  <b>↓</b> Doctor workload <b>↓</b> Staff workload
                </div>
                <button onClick={handleCascade}>
                  Analyze +{admissionsChange}% Admissions Cascade
                </button>
              </section>

              <section className="card">
                <div className="section-title">
                  <Play size={18} /> What-if Simulator
                </div>
                <label>Simulated Admissions change: {admissionsChange}%</label>
                <input
                  type="range"
                  min="-20"
                  max="50"
                  value={admissionsChange}
                  onChange={(e) => setAdmissionsChange(e.target.value)}
                />
                <button onClick={handleSimulation}>Run Fast Scenario</button>
                {simulation && (
                  <div className="simulation">
                    <strong>Simulated Impact Result</strong>
                    <p>
                      Beds {simulation.simulated.bed_occupancy_pct}% · ICU{" "}
                      {simulation.simulated.icu_occupancy_pct}%
                    </p>
                    <p>
                      Doctor workload {simulation.simulated.doctor_workload} pts/dr
                    </p>
                    <b>
                      Risk {simulation.simulated.risk_score} ·{" "}
                      {simulation.simulated.risk_level || "calculated"}
                    </b>
                  </div>
                )}
              </section>
            </div>

            <section className="card decision">
              <div className="section-title">
                <Activity size={18} /> Operational Decision Action Center
              </div>
              <p><b>Current issue:</b> Bed and emergency pressure are elevated above safe buffer.</p>
              <p><b>Forecast:</b> Trend indicates peak strain approaching over the next 7 days.</p>
              <p>
                <b>Recommendation:</b> Review bed allocation, activate step-down discharge protocol,
                and prepare float pool coverage.
              </p>
              <div style={{ marginTop: 14 }}>
                <button onClick={() => setPage("decision")}>
                  Open Decision Center
                </button>
              </div>
            </section>
          </>
        )}

        {page === "hindsight" && (
          <section className="card">
            <div className="section-title">
              <BrainCircuit size={18} /> Hindsight Context Retrieval
            </div>
            <p className="muted">
              Historical vector similarity and context retrieval — explainable case-based reasoning.
            </p>
            {!hindsight ? (
              <p>Loading historical matching events...</p>
            ) : (
              hindsight.matches.map((m) => (
                <div className="history-row" key={m.date}>
                  <div>
                    <strong>{m.date}</strong>
                    <span>{m.department}</span>
                  </div>
                  <div className="score">{m.similarity_score}%</div>
                  <div>
                    <b>{m.situation}</b>
                    <p><b>Action Taken:</b> {m.previous_action}</p>
                    <small><b>Verified Outcome:</b> {m.outcome} ({m.outcome_status})</small>
                  </div>
                </div>
              ))
            )}
          </section>
        )}

        {page === "forecast" && (
          <section className="card">
            <div className="section-title">
              <BarChart3 size={18} /> Demand Forecasting Engine
            </div>
            <div className="controls">
              <label>
                Select Metric to Forecast:
                <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                  <option value="admissions">Admissions</option>
                  <option value="emergency_cases">Emergency Cases</option>
                  <option value="bed_occupancy">Bed Occupancy</option>
                  <option value="icu_occupancy">ICU Occupancy</option>
                </select>
              </label>
            </div>
            {forecast && (
              <>
                <p>
                  Method: <b>{forecast.method}</b> · Horizon: {forecast.horizon} days ·
                  Model Quality: <span style={{ color: "#5fe0d3" }}>{forecast.quality}</span>
                </p>
                <div className="chart">
                  <ResponsiveContainer width="100%" height={360}>
                    <LineChart data={chartData}>
                      <XAxis dataKey="day" stroke="#8094aa" />
                      <YAxis stroke="#8094aa" />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="historical"
                        name="Historical (Actual)"
                        stroke="#59c7bd"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="forecast"
                        name="Projected Forecast"
                        stroke="#ffbd5a"
                        strokeWidth={2}
                        strokeDasharray="4 4"
                        dot
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <small>{forecast.capacity_note}</small>
              </>
            )}
          </section>
        )}

        {page === "cascade" && (
          <section className="card">
            <div className="section-title">
              <GitBranch size={18} /> CascadeFlow Systemic Impact
            </div>
            <p>
              Scenario: Emergency Admissions change of <b>+{admissionsChange}%</b>
            </p>
            {!cascade ? (
              <button onClick={handleCascade}>Analyze Cascade</button>
            ) : (
              <div className="cascade-list">
                {cascade.nodes.map((n, i) => (
                  <div className="cascade-node" key={`${n.label}-${i}`}>
                    <div className="node-number">{i + 1}</div>
                    <div>
                      <strong>{n.label}</strong>
                      <span style={{ color: "#ffbd5a" }}>
                        Expected strain change: +{n.change_pct}%
                      </span>
                      <small>{n.reason}</small>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <small>{cascade?.note}</small>
          </section>
        )}

        {page === "whatif" && (
          <section className="card">
            <div className="section-title">
              <Play size={18} /> What-if Multi-factor Simulator
            </div>
            <p className="muted">
              Simulate the ripple effects of demand surges, surge staffing, and capacity reallocations.
            </p>

            <div className="simulator-controls-grid">
              <div>
                <label>Admissions Change: <b>{admissionsChange > 0 ? `+${admissionsChange}` : admissionsChange}%</b></label>
                <input
                  type="range"
                  min="-20"
                  max="50"
                  value={admissionsChange}
                  onChange={(e) => setAdmissionsChange(e.target.value)}
                />
              </div>

              <div>
                <label>Emergency Cases Change: <b>{emergencyChange > 0 ? `+${emergencyChange}` : emergencyChange}%</b></label>
                <input
                  type="range"
                  min="-20"
                  max="50"
                  value={emergencyChange}
                  onChange={(e) => setEmergencyChange(e.target.value)}
                />
              </div>

              <div>
                <label>Doctor Availability Change: <b>{doctorChange > 0 ? `+${doctorChange}` : doctorChange}%</b></label>
                <input
                  type="range"
                  min="-30"
                  max="50"
                  value={doctorChange}
                  onChange={(e) => setDoctorChange(e.target.value)}
                />
              </div>
            </div>

            <div style={{ margin: "14px 0" }}>
              <button onClick={handleSimulation}>Simulate Scenario Outcome</button>
            </div>

            {simulation && (
              <div className="compare">
                <div>
                  <span>Current Baseline State</span>
                  <b>Bed Occupancy: {simulation.baseline.bed_occupancy_pct}%</b>
                  <b>ICU Occupancy: {simulation.baseline.icu_occupancy_pct}%</b>
                  <b>Doctor Workload: {simulation.baseline.doctor_workload} pts/dr</b>
                  <small>Emergency Pressure: {simulation.baseline.emergency_pressure_pct}%</small>
                </div>
                <div>
                  <span style={{ color: "#ffbd5a" }}>Projected Simulated State</span>
                  <b>Bed Occupancy: {simulation.simulated.bed_occupancy_pct}%</b>
                  <b>ICU Occupancy: {simulation.simulated.icu_occupancy_pct}%</b>
                  <b>Doctor Workload: {simulation.simulated.doctor_workload} pts/dr</b>
                  <strong>
                    Risk Score: {simulation.simulated.risk_score} ·{" "}
                    {(simulation.simulated.risk_level || "calculated").toUpperCase()}
                  </strong>
                </div>
              </div>
            )}
            <p className="disclaimer">
              This is an aggregate operational scenario estimate. It does not automatically modify
              hospital resource assignments.
            </p>
          </section>
        )}

        {page === "upload" && (
          <DataUpload onDataCommitted={loadDashboard} />
        )}

        {page === "decision" && (
          <section className="card">
            <div className="section-title">
              <ShieldAlert size={18} /> Executive Decision Center & Audit Log
            </div>
            <p className="muted">
              Synthesize insights across all modules, record decisive administrative actions, and maintain an immutable operational audit trail.
            </p>

            <div className="decision-stack">
              <div>
                <span>Current situation</span>
                <b>Bed and emergency capacity pressure elevated above safe buffer.</b>
              </div>
              <div>
                <span>Historical memory</span>
                <b>{dashboard.hindsight.similarity_score}% similar past event found ({dashboard.hindsight.date}).</b>
              </div>
              <div>
                <span>Forecast signal</span>
                <b>Peak demand trend continues across the next 7-day horizon.</b>
              </div>
              <div>
                <span>Cascade analysis</span>
                <b>Strain propagates from Emergency to ICU and inpatient doctor workload.</b>
              </div>
              <div>
                <span>Recommended action</span>
                <b>Activate discharge lounge, authorize 2 float doctors, review ICU step-downs.</b>
              </div>
            </div>

            <div className="decision-form-box">
              <h4>Record Administrator Action</h4>
              <div style={{ margin: "10px 0" }}>
                <label style={{ display: "block", marginBottom: 6, fontSize: 13, color: "#8fa4ba" }}>
                  Action Taken:
                </label>
                <input
                  type="text"
                  value={customAction}
                  onChange={(e) => setCustomAction(e.target.value)}
                  placeholder="Enter administrator intervention..."
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    background: "#13253a",
                    border: "1px solid #29415b",
                    borderRadius: 7,
                    color: "white",
                  }}
                />
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <button
                  onClick={saveDecision}
                  disabled={isSubmittingDecision || !customAction}
                >
                  {isSubmittingDecision ? "Saving to Database..." : "Commit Administrator Decision"}
                </button>
                {decisionStatus && <span className="success">{decisionStatus}</span>}
              </div>
            </div>

            <div className="decisions-history-section" style={{ marginTop: 24 }}>
              <h3>Historical Decision Audit Trail (Database Persisted)</h3>
              {decisions.length === 0 ? (
                <p className="muted">No decision records found.</p>
              ) : (
                <div className="decisions-table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Department</th>
                        <th>Issue</th>
                        <th>Administrator Action</th>
                        <th>Status</th>
                        <th>Recorded By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {decisions.map((d) => (
                        <tr key={d.id}>
                          <td>{d.timestamp || "Just now"}</td>
                          <td>{d.department}</td>
                          <td>{d.issue}</td>
                          <td><b>{d.administrator_action}</b></td>
                          <td>
                            <span className={`status-pill ${d.outcome}`}>
                              {d.outcome.toUpperCase()}
                            </span>
                          </td>
                          <td>{d.recorded_by}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;