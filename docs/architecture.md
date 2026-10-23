# Architecture

```
Browser (React 18 + Vite, Vercel)
  │  REST (JSON, Bearer token)        SSE (POST /api/v1/chat)
  ▼                                    ▼
FastAPI (Render)
  ├─ core/config.py      thresholds, colours, units, formulas (one source of truth)
  ├─ core/security.py    PBKDF2 passwords, signed tokens, Admin/Analyst/Viewer
  ├─ state_service       current state → dashboard, alerts, recommendations, chat tools
  ├─ alert_service       threshold + predictive (forecast) + low-stock, ack/snooze state
  ├─ upload_service      schema, PII masking, row errors, batches, rollback
  ├─ audit_service       who did what and when (+ CSV export)
  ├─ rag_service         ingest → embed (Voyage or local) → pgvector / in-memory → hybrid retrieve
  └─ chat_service        Claude tool loop (live tools) + data-only fallback
  │
  ▼
PostgreSQL (prod) / SQLite (local)
  resource_snapshots · upload_batches · audit_log · alert_state · rag_chunks
  chat_sessions · chat_messages · decisions · users · …
```

Data changes (upload commit / rollback, decisions, alert state) publish to
`services/data_events.py`; the RAG index subscribes and refreshes itself.
