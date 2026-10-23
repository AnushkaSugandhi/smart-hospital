# Smart Hospital Decision Support System (SH-DSS)
**Vardhaman General Hospital — Operations Intelligence Platform**

An end-to-end, full-stack decision intelligence and operational command center designed for hospital executive administrators, chief medical officers, and department directors.

The system operationalizes the **Observe → Remember → Predict → Analyze → Decide** cognitive workflow:
- **Observe:** Real-time resource pressure monitoring (bed occupancy, ICU saturation, physician workload, emergency pressure, dynamic composite risk scoring).
- **Remember (Hindsight):** Explainable case-based historical memory retrieval matching current pressure profiles against past incidents to inspect historical interventions and outcomes.
- **Predict (Forecasting):** 7-day predictive demand forecasting across admissions, emergencies, bed occupancy, and ICU utilization using moving-average and autoregressive trend models.
- **Analyze (CascadeFlow):** Transparent cross-department strain propagation engine quantifying how volume shocks cascade from triage to inpatient wards and medical staff.
- **Simulate (What-if):** Multi-factor scenario sandbox to stress-test capacity adjustments, physician availability shifts, and admission spikes with instant simulated risk scores.
- **Decide (Decision Center):** Executive decision logger with audit trail permanently recorded to an operational database (PostgreSQL / SQLite).
- **Upload & Quality Engine:** Automated profiling, schema validation, duplicate detection, and database import for operational CSV/XLSX data.

---

## Architecture

```
                                    +------------------------------+
                                    |       React 18 + Vite        |
                                    |   Hospital Command Center    |
                                    +--------------+---------------+
                                                   |
                                            HTTPS / REST API
                                                   |
                                    +--------------v---------------+
                                    |       FastAPI Backend        |
                                    |    Python 3.11+ / Uvicorn    |
                                    +--------------+---------------+
                                                   |
                           +-----------------------+-----------------------+
                           |                                               |
              +------------v------------+                     +------------v------------+
              |    PostgreSQL (Prod)    |                     |   SQLite (Local Auto)   |
              |  Supabase / Neon/ Render|                     |    smart_hospital.db    |
              +-------------------------+                     +-------------------------+
```

---

## Project Structure

```
smart-hospital/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   ├── database.py         # SQLAlchemy engine with PostgreSQL & SQLite auto-fallback
│   │   │   ├── models.py           # Relational schema (snapshots, events, decisions, users)
│   │   │   └── init_db.py          # Auto-migration & seed data initialization
│   │   ├── seed/
│   │   │   └── generate_data.py    # Synthetic operational snapshot generator
│   │   ├── services/
│   │   │   ├── cascade_service.py  # Cross-department strain cascade analysis
│   │   │   ├── forecast_service.py # 7-day statistical forecasting engine
│   │   │   ├── hindsight_service.py# Vector similarity & historical matching
│   │   │   ├── risk_engine.py      # Multi-factor composite risk scoring
│   │   │   ├── simulation_service.py# Multi-parameter what-if simulator
│   │   │   └── upload_service.py   # Profiling, validation & database committing
│   │   └── main.py                 # FastAPI application, routes, and lifespan
│   ├── requirements.txt            # Python dependencies
│   ├── Procfile                    # Render production process command
│   ├── .env.example                # Backend configuration template
│   └── test_api.py                 # Comprehensive automated test suite
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── DataUpload.jsx      # CSV/XLSX upload, profiling, and DB commit UI
│   │   ├── services/
│   │   │   └── api.js              # Centralized API service with auth & error handling
│   │   ├── App.jsx                 # Main Command Center UI, charts, and decision center
│   │   ├── index.css               # Command center dark theme & responsive styles
│   │   └── main.jsx                # React root entry point
│   ├── package.json                # Frontend dependencies (React 18, Recharts, Lucide)
│   ├── vercel.json                 # Vercel SPA routing configuration
│   └── .env.example                # Frontend environment template
├── data/
│   └── test_hospital_data.csv      # Sample operational data for testing upload
└── README.md                       # Complete documentation & deployment guide
```

---

## Quickstart Guide (Local Development)

### Prerequisites
- **Python 3.11+**
- **Node.js LTS (v18+)**
- **Git**

---

### Step 1: Start the FastAPI Backend

Open a terminal in the project directory:

```powershell
cd smart-hospital/backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload
```

The backend starts at:
- **API Base:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/api/v1/health`

> **Note on Database:** The backend automatically initializes and seeds all database tables on launch. If PostgreSQL is not configured, it seamlessly uses SQLite (`smart_hospital.db`) with zero configuration required.

---

### Step 2: Start the React Frontend

Open a second terminal window:

```powershell
cd smart-hospital/frontend

# Install node dependencies
npm install

# Start Vite development server
npm run dev
```

Open your browser to:
- **`http://localhost:5173`**

---

## Running the Automated Test Suite

Run the full pytest backend verification suite:

```powershell
cd smart-hospital/backend
.venv\Scripts\pytest.exe test_api.py -v
```

All 12 core tests will execute:
- `test_root`: Root API ping
- `test_health`: Database connection status
- `test_dashboard`: Dashboard metrics and risk scores
- `test_alerts`: Threshold alert engine
- `test_resource_history`: Database snapshots
- `test_hindsight`: Historical similarity engine
- `test_forecast`: 7-day projection calculations
- `test_cascade`: CascadeFlow cross-department impact
- `test_simulation`: What-if scenario calculations
- `test_decisions_flow`: Decision persistence and retrieval
- `test_auth_login`: Administrative authentication
- `test_upload_profile_and_commit`: CSV profiling and database import

To test the frontend production build:
```powershell
cd smart-hospital/frontend
npm run build
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status and metadata |
| `GET` | `/api/v1/health` | Health and database connectivity status |
| `GET` | `/api/v1/dashboard/summary` | Real-time occupancy, staff loads, risk score, alerts |
| `GET` | `/api/v1/alerts` | Active operational threshold alerts |
| `GET` | `/api/v1/resources/history` | Historical resource snapshots from database |
| `POST` | `/api/v1/hindsight/search` | Case-based vector similarity matching |
| `GET` | `/api/v1/forecast` | 7-day statistical forecasting (`admissions`, `icu`, etc.) |
| `POST` | `/api/v1/cascadeflow/analyze` | Cross-department strain cascade analysis |
| `POST` | `/api/v1/simulations` | What-if simulation engine |
| `GET` | `/api/v1/decisions` | Retrieve persisted administrator decisions |
| `POST` | `/api/v1/decisions` | Persist an administrator decision to database |
| `POST` | `/api/v1/uploads/profile` | Profile & validate CSV/XLSX data quality |
| `POST` | `/api/v1/uploads/commit` | Commit cleaned operational data to database |
| `POST` | `/api/v1/auth/login` | Administrator authentication |
| `GET` | `/api/v1/auth/me` | Current user profile |

---

## Data Upload Format

The Data Upload module accepts `.csv` and `.xlsx` files with the following schema:

```csv
date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload
2026-10-01,Emergency,80,19,0.90,0.86,11.7,9.0
2026-10-02,Emergency,82,20,0.92,0.88,12.1,9.4
2026-10-03,Emergency,84,21,0.94,0.90,12.5,9.6
```

1. Go to **Data Upload** in the navigation bar.
2. Select your file or click **Load Sample Surge Data**.
3. Click **Upload and Validate** to view the Data Quality Report (total records, missing values, duplicates, dates).
4. Click **Save Valid Records to Database** to permanently commit the data into the operational database.

---

## Production Deployment Guide

### Deploy Backend to Render

1. Create a repository on GitHub and push the project.
2. Log into [Render](https://render.com).
3. Create a **New Web Service**:
   - **Root Directory:** `smart-hospital/backend`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add:
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: *(Your PostgreSQL URL, e.g. from Render PostgreSQL or Neon)*
   - `FRONTEND_ORIGIN`: `https://your-frontend.vercel.app`
5. Click **Deploy**. Your API will be live at `https://YOUR-APP.onrender.com`.

### Deploy Frontend to Vercel

1. Log into [Vercel](https://vercel.com).
2. Click **Add New Project** and select your GitHub repository.
3. Set **Root Directory** to `smart-hospital/frontend`.
4. Under **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://YOUR-APP.onrender.com/api/v1`
5. Click **Deploy**. Your frontend is live with automatic global CDN and SSL.

---

## Ethical and Operational Disclaimer

This platform is an operational decision-support demonstration system utilizing synthetic hospital operational data. It is intended exclusively for operational administrative resource management and capacity planning. It does not provide medical or clinical diagnostic recommendations and does not automate patient care decisions.
