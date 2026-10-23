# Smart Hospital Decision Support System (SH-DSS)
**Vardhaman General Hospital — Operations Intelligence Platform**

A full-stack decision-support command center for hospital administrators, analysts and coordinators. It follows an **Observe → Remember → Predict → Analyze → Decide** workflow, and adds an AI assistant that answers questions from live hospital data and policies, with sources.

- **Observe:** Live bed, ICU, doctor, emergency and resource pressure (ventilators, operation theatres, nurses, oxygen, blood by group). Every number has a unit, a status (green/amber/red) and a formula tooltip. KPI cards show sparklines and change vs the previous day.
- **Alerts:** Threshold, **predictive** ("ICU likely full in about 6 hours") and low-stock alerts, with acknowledge / snooze stored in the database.
- **Remember (Hindsight):** Finds past situations similar to today and shows what was done and how it turned out.
- **Predict (Forecasting):** 3–14 day forecasts (Holt-Winters, with a moving-average fallback for short histories).
- **Analyze (CascadeFlow):** An animated flow from Emergency to Wards to ICU to Staff, showing how a surge spreads.
- **Simulate (What-if):** Six scenario sliders, scored with the same risk formula as the dashboard.
- **Decide:** "What should I do now?" lists the top 3 actions, each with why, simulated impact, and Approve/Dismiss. Every choice is logged to the Decision Center.
- **Ask AI:** Chat (floating panel and full page) with streaming answers, tool calls for numbers, RAG for history and policies, citations, charts, and a low-confidence label.
- **Data & admin:** An Upload > Validate > Preview > Commit stepper with personal-data masking, version history with rollback, role-based access (Admin / Analyst / Viewer), and a filterable, exportable Audit Log.

> Decision support only. AI supports decisions and does not replace medical judgment. All bundled data is synthetic.

---

## Architecture

```
React 18 + Vite (Vercel)                    FastAPI (Render)                         Storage
───────────────────────                     ────────────────                         ───────
Shell · AppContext · hash router   ─REST─►  api/auth  (signed tokens, RBAC)    ┌──►  PostgreSQL (prod) / SQLite (local)
Pages: Overview, Hindsight, ...    ─SSE──►  api/chat  ──► chat_service ───────┤      resource_snapshots (+batch_id,
ChatPanel / Ask AI (streaming)              api/data  (uploads, audit)         │        superseded_by_batch)
                                            api/ops   (alerts, next actions)   │      upload_batches · audit_log
                                            main.py   (dashboard, forecast…)   │      alert_state · rag_chunks
                                                                               │      chat_sessions · chat_messages
                         core/config.py ── single source of thresholds,        │
                         colours, units, formulas (served at /api/v1/config)   └──►  pgvector (if available) or
                                                                                      in-memory numpy index
                         chat_service ─► tools: dashboard, forecast, simulation, alerts, compare
                                      └► rag_service: hybrid retrieval over snapshots, decisions,
                                         alerts, past events, audit (Admin), docs/policies/*.md
                                      └► Claude (Anthropic API) — or a data-only answer without a key
```

### How the chatbot answers

1. **Retrieve:** `rag_service.retrieve()` applies role and metadata filters (department and dates parsed from the question), scores chunks with vector similarity plus BM25 keyword matching, reranks with MMR, and returns the top 6. Results are cached per index version.
2. **Numbers via tools:** Claude calls `get_dashboard_summary`, `get_forecast`, `run_simulation`, `get_alerts` and `compare_periods`. These hit the same services as the dashboard, so the chatbot never guesses numbers from text.
3. **Grounded answer:** The system prompt requires answers only from tool results and snippets, citations like `[S2]`, and "I don't know" when the data is missing. The UI shows source chips, mini charts and tables, and "Open in Forecasting" / "Run in Simulator" buttons, plus a **low confidence** label when sources are weak.
4. **Without an API key**, or if the API fails, the same tools and retrieval produce a deterministic data-only answer, so the feature still works on free tiers and in tests.

The index is rebuilt automatically after every upload commit or rollback. Rollback also deletes the chunks tagged with that batch. Only aggregated or scrubbed text is indexed: emails, phone numbers and ID numbers are removed, and decision authors are reduced to their role.

---

## Project structure (key files)

```
backend/app/
├── core/config.py            # thresholds, colours, capacity, risk weights, units, formulas
├── core/security.py          # PBKDF2 passwords, HMAC tokens, require_role()
├── api/auth.py · data.py · ops.py · chat.py   # new routers
├── db/models.py              # + UploadBatch, AuditLog, AlertState, RagChunk, ChatSession, ChatMessage
├── db/init_db.py             # create tables, add missing columns, seed, secure users
└── services/
    ├── metrics_service.py    # counts → %, status, formula strings
    ├── risk_engine.py        # score + Low/Medium/High/Critical + factor breakdown
    ├── state_service.py      # the one "current state" used by dashboard, alerts, chat
    ├── alert_service.py      # threshold, predictive and stock alerts + ack/snooze
    ├── resources_service.py  # ventilators, OT, nurses, oxygen, blood cards
    ├── recommendation_service.py  # "What should I do now?"
    ├── upload_service.py     # schema, PII masking, row errors, batches, rollback
    ├── audit_service.py      # write / query / CSV export
    ├── rag_service.py        # ingest, embed, store, hybrid retrieval
    └── chat_service.py       # tools, Claude streaming loop, data-only fallback
frontend/src/
├── App.jsx                   # shell, routes, page transitions
├── context/AppContext.jsx    # data loading, auto-refresh, filters, roles
├── config/metrics.js · pages.js
├── components/               # KpiCard, Sparkline, RiskGauge, AlertBanner, AlertsPanel, UploadStepper,
│                             # AuditTable, CascadeCanvas, ForecastChart, NextActions, Tour, GlobalSearch…
├── chat/                     # ChatContext, ChatPanel, ChatView, MiniChart, Markdown
└── pages/                    # Overview, Hindsight, Forecasting, CascadeFlow, Simulator,
                              # DecisionCenter, AskAI, DataUpload, AuditLog, LoginPage
docs/policies/*.md            # hospital SOPs indexed by the assistant
```

---

## Run locally

Prerequisites: Python 3.11+, Node.js 18+.

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # optional: add ANTHROPIC_API_KEY for AI-written answers
uvicorn app.main:app --reload         # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                           # http://localhost:5173
```

The database is created, migrated and seeded on startup. If `DATABASE_URL` is unset or unreachable, SQLite is used.

### Demo accounts

| Username | Password | Role | Can |
|---|---|---|---|
| `admin` | `admin123` | Admin | Everything, including rollback and the audit log |
| `analyst` | `analyst123` | Analyst | Upload, record decisions, acknowledge/snooze alerts |
| `viewer` | `viewer123` | Viewer | Read dashboards, ask the AI |
| `cmo` | `admin123` | Analyst | (existing account, migrated from "Chief Medical Officer") |

Roles are enforced on the backend for every route, not just hidden in the UI. Change these passwords before any real deployment.

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file | PostgreSQL URL in production |
| `ENVIRONMENT` | `development` | `production` enables strict CORS |
| `FRONTEND_ORIGIN` | – | Allowed frontend origin(s), comma-separated |
| `SECRET_KEY` | random at startup | Signs login tokens. **Set it in production**, or everyone is signed out on restart |
| `TOKEN_TTL_HOURS` | `12` | Session length |
| `ANTHROPIC_API_KEY` | – | Enables Claude-written answers. Without it, the chatbot gives data-only answers |
| `LLM_MODEL` | `claude-opus-5-5` | Claude model for chat |
| `LLM_EFFORT` | `low` | `low` / `medium` / `high`; lower is faster |
| `LLM_PROVIDER` | auto | Set to `offline` to force data-only answers |
| `VOYAGE_API_KEY` | – | Enables Voyage AI embeddings; otherwise a local hashing embedder is used |
| `EMBEDDING_PROVIDER` | `voyage` if key set, else `local` | Override the embedder |
| `EMBEDDING_DIM` | `512` (voyage) / `384` (local) | Vector size. Changing it re-embeds the index |
| `POLICY_DOCS_DIR` | `../docs/policies` | Folder of Markdown policies/SOPs to index |
| `CHAT_RATE_LIMIT_PER_MIN` | `20` | Questions per user per minute |

API keys are read only by the backend and never sent to the browser.

### Frontend (`frontend/.env`)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL, e.g. `https://smart-hospital-api.onrender.com/api/v1` |

---

## Data upload format

Required columns (unchanged, so existing CSVs keep working):

| Column | Type | Notes |
|---|---|---|
| `date` | date | `YYYY-MM-DD` |
| `department` | text | e.g. `Emergency` |
| `admissions` | number | per day |
| `emergency_cases` | number | active cases |
| `bed_occupancy` | ratio | 0–1 (0–100 also accepted and converted) |
| `icu_occupancy` | ratio | 0–1 (0–100 also accepted) |
| `doctor_workload` | number | patients per doctor |
| `staff_workload` | number | patients per staff member |

New **optional** columns:

| Column | Type | Used for |
|---|---|---|
| `ventilators_total`, `ventilators_in_use` | integer | Ventilator card (in use cannot exceed total) |
| `ot_total`, `ot_in_use` | integer | Operation theatre card |
| `nurses_on_duty`, `nurses_required` | integer | Nurse coverage card |
| `oxygen_stock_hours` | number | Oxygen card (warning < 24 h, critical < 12 h) |
| `blood_a_pos`, `blood_a_neg`, `blood_b_pos`, `blood_b_neg`, `blood_o_pos`, `blood_o_neg`, `blood_ab_pos`, `blood_ab_neg` | integer | Blood stock by group (low < 10 units, critical < 5) |

- Formats: `.csv`, `.xlsx` · limit 5 MB / 20,000 rows. Download the template from the Data Upload page or `GET /api/v1/uploads/template`.
- Columns that look personal (names, phone numbers, emails, ID numbers) are masked in the preview and **never stored**.
- Rows with errors are listed with row and column and skipped. Valid rows are committed as a **batch** that can be previewed and rolled back. A rollback restores any earlier values the batch replaced.
- See `data/sample_full_upload.csv` for an example with every column.

---

## Single source of truth for thresholds

`backend/app/core/config.py` defines capacity, the colour rule (**green < 70%, amber 70–85%, red > 85%**), risk weights and levels (Low 0–30, Medium 31–60, High 61–80, Critical 81–100), low-stock floors, units and formulas. The API returns a `status` for every metric and serves the config at `/api/v1/config`. Occupancy percentages are always computed from the same bed counts shown on the cards.

---

## Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q
```

- `test_api.py`: the original 13 tests, unchanged except that the client now signs in (all endpoints require a role).
- `test_metrics.py`: count-based percentages, the colour rule, risk breakdown, doctor-overload estimate, alerts.
- `test_phase2.py`: RBAC, audit log and CSV export, acknowledge/snooze, predictive alerts, upload PII masking and row errors, batches and rollback ordering, optional resources.
- `test_chat.py`: streaming chat, live-number grounding, citations, "I don't know", history, feedback, audit, role-filtered retrieval, anonymisation, rollback removal from the index, and the Claude tool loop (fake client, no network).

Tests use their own `test_smart_hospital.db` and never touch your dev database.

---

## API reference (v1)

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `POST` | `/auth/login` | – | Sign in, returns a signed token |
| `GET` | `/auth/me` | Viewer | Current user from the token |
| `GET` | `/config` | – | Thresholds, colours, units, formulas |
| `GET` | `/dashboard/summary?department=` | Viewer | State with `generated_at`, trends, resources, risk breakdown |
| `GET` | `/alerts?include_all=` | Viewer | Active (or all) alerts with state |
| `POST` | `/alerts/{id}/acknowledge` · `/alerts/{id}/snooze` | Analyst | Persisted alert state |
| `GET` | `/recommendations/next` | Viewer | Top 3 "What should I do now?" actions |
| `POST` | `/recommendations/next/{id}/decide` | Analyst | Approve/dismiss → Decision Center |
| `GET` | `/resources` · `/resources/history` | Viewer | Resource cards · daily series |
| `GET` | `/forecast` · `POST /simulations` · `POST /cascadeflow/analyze` · `POST /hindsight/search` | Viewer | Analytics |
| `GET`/`POST` | `/decisions` | Viewer / Analyst | Decision log |
| `GET` | `/uploads/schema` · `/uploads/template` | Viewer | Upload guidance |
| `POST` | `/uploads/profile` · `/uploads/commit` | Analyst | Validate · commit as batch |
| `GET` | `/uploads/batches` · `/uploads/batches/{id}` | Viewer / Analyst | Version history · preview |
| `POST` | `/uploads/batches/{id}/rollback` | Admin | Undo an upload |
| `GET` | `/audit` · `/audit/export` · `/audit/meta` | Admin | Audit log, CSV export, filter values |
| `POST` | `/chat` | Viewer | SSE stream: `meta`, `status`, `token`, `chart`, `done`, `error` |
| `GET` | `/chat/suggestions` · `/chat/sessions` · `/chat/sessions/{id}` | Viewer | Suggestions and own history |
| `DELETE` | `/chat/sessions/{id}` | Viewer | Delete own chat |
| `POST` | `/chat/messages/{id}/feedback` | Viewer | Thumbs up/down |
| `POST` | `/chat/reindex` | Admin | Rebuild the knowledge index |

---

## Deployment (free tier)

### Backend on Render
`render.yaml` defines the web service and a free PostgreSQL database. Set `FRONTEND_ORIGIN`, and optionally `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY`, in the Render dashboard. `SECRET_KEY` is generated by Render. New tables and columns are added automatically on startup.

**pgvector:** if the database allows `CREATE EXTENSION vector`, embeddings are also stored and searched in PostgreSQL. Otherwise the in-memory index is used automatically. The pgvector path was written for this upgrade but has not yet been run against a live PostgreSQL instance, so check the startup logs after the first deploy.

### Frontend on Vercel
Root directory `frontend`, environment variable `VITE_API_BASE_URL=https://YOUR-APP.onrender.com/api/v1`.

---

## Accessibility & motion

Keyboard navigation (skip link, focus rings, Esc closes panels, Ctrl+K search), aria labels, status always shown as icon + text, a table view for charts, and a dark/light theme toggle. All animations (count-up, drawing charts, gauge glow, cascade particles, ECG background) turn off under `prefers-reduced-motion`.

## Ethical and operational disclaimer

This platform uses synthetic operational data and is intended for administrative capacity planning. It does not provide clinical or diagnostic recommendations and does not automate patient care decisions.
