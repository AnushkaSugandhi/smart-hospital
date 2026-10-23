"""Retrieval-augmented knowledge for the "Ask Smart Hospital" assistant.

Ingest -> embed -> store -> hybrid retrieve.

* Ingest: weekly per-department snapshot summaries, decisions, current alerts,
  historical events, audit activity (Admin-only) and Markdown policies/SOPs.
  Everything indexed is aggregated or scrubbed of personal data.
* Embed: Voyage AI when VOYAGE_API_KEY is set, otherwise a local hashing
  embedder (no download, no key) so free-tier hosts and tests work offline.
* Store: rows in rag_chunks. On PostgreSQL with pgvector, vectors also go in
  a vector column and are searched in SQL; otherwise an in-memory numpy index.
* Retrieve: vector + keyword (BM25) scores, metadata filters, role filter,
  MMR rerank, LRU cache keyed on the index version.
"""
import hashlib
import json
import logging
import math
import os
import re
import threading
from collections import Counter, OrderedDict, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import text

from app.core.security import ROLES
from app.db.database import SessionLocal, engine
from app.db.models import AuditLog, DecisionRecord, HistoricalEvent, RagChunk
from app.services import data_events, snapshot_service
from app.services.upload_service import scrub_text

logger = logging.getLogger("smart_hospital.rag")

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "voyage" if os.getenv("VOYAGE_API_KEY") else "local").lower()
# Voyage supports 256/512/1024/2048 output dimensions; the local embedder any size.
EMBED_DIM = int(os.getenv("EMBEDDING_DIM", "512" if EMBEDDING_PROVIDER == "voyage" else "384"))
VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3.5-lite")
POLICY_DIR = Path(os.getenv("POLICY_DOCS_DIR", Path(__file__).resolve().parents[3] / "docs" / "policies"))
TOP_K = 6

_lock = threading.RLock()
_state = {"version": 0, "dirty": True, "matrix": None, "rows": None, "pgvector": None}
_cache: "OrderedDict[tuple, list]" = OrderedDict()
_CACHE_SIZE = 128

_TOKEN = re.compile(r"[a-z0-9][a-z0-9+\-]*")
_STOP = set("the a an of to in on for and or is are was were be by with at as it this that what which when how do does did i we our my me".split())


# ---- Embedding ---------------------------------------------------------------
def tokenize(value: str) -> list[str]:
    return [t for t in _TOKEN.findall(value.lower()) if t not in _STOP]


def _local_embed(value: str) -> np.ndarray:
    """Signed feature hashing over words and word bigrams, L2-normalised."""
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    tokens = tokenize(value)
    feats = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    for feat, count in Counter(feats).items():
        h = int(hashlib.md5(feat.encode()).hexdigest(), 16)
        vec[h % EMBED_DIM] += (1 if (h >> 8) & 1 else -1) * (1 + math.log(count))
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def _voyage_embed(texts: list[str], input_type: str) -> list[np.ndarray]:
    import httpx
    resp = httpx.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"},
        json={"input": texts, "model": VOYAGE_MODEL, "input_type": input_type, "output_dimension": EMBED_DIM},
        timeout=30,
    )
    resp.raise_for_status()
    return [np.asarray(d["embedding"], dtype=np.float32) for d in resp.json()["data"]]


def embedding_model_name() -> str:
    return f"voyage:{VOYAGE_MODEL}:{EMBED_DIM}" if EMBEDDING_PROVIDER == "voyage" else f"local-hash:{EMBED_DIM}"


def embed(texts: list[str], input_type: str = "document") -> list[np.ndarray]:
    if EMBEDDING_PROVIDER == "voyage":
        try:
            out = []
            for i in range(0, len(texts), 64):
                out.extend(_voyage_embed(texts[i:i + 64], input_type))
            return out
        except Exception as exc:  # keep answering with the local embedder
            logger.warning("Voyage embedding failed (%s); using local embedder.", exc)
    return [_local_embed(t) for t in texts]


# ---- Chunk builders ----------------------------------------------------------
def _pct(v):
    return f"{v * 100:.1f}%" if v is not None else "n/a"


def _week_key(day: str) -> tuple[int, int]:
    y, w, _ = date.fromisoformat(day).isocalendar()
    return y, w


def _snapshot_chunks(db) -> list[dict]:
    rows = [r.to_dict() for r in snapshot_service.active_query(db).all()]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["department"], _week_key(r["date"]))].append(r)

    chunks = []
    for (dept, (year, week)), items in groups.items():
        items.sort(key=lambda r: r["date"])
        start, end = items[0]["date"], items[-1]["date"]

        def stats(key, ratio=False):
            vals = [r[key] for r in items if r.get(key) is not None]
            if not vals:
                return "n/a"
            avg, lo, hi = sum(vals) / len(vals), min(vals), max(vals)
            return (f"avg {_pct(avg)} (low {_pct(lo)}, peak {_pct(hi)})" if ratio
                    else f"avg {avg:.1f} (low {lo:g}, peak {hi:g})")

        summary = (
            f"{dept} department, week {week} of {year} ({start} to {end}). "
            f"Admissions {stats('admissions')}. Emergency cases {stats('emergency_cases')}. "
            f"Bed occupancy {stats('bed_occupancy', True)}. ICU occupancy {stats('icu_occupancy', True)}. "
            f"Doctor workload {stats('doctor_workload')} patients per doctor. "
            f"Staff workload {stats('staff_workload')} patients per staff."
        )
        lines = []
        for r in items:
            extra = []
            if r.get("ventilators_in_use") is not None and r.get("ventilators_total"):
                extra.append(f"ventilators {r['ventilators_in_use']:g}/{r['ventilators_total']:g}")
            if r.get("oxygen_stock_hours") is not None:
                extra.append(f"oxygen {r['oxygen_stock_hours']:g} h")
            if r.get("nurses_on_duty") is not None and r.get("nurses_required"):
                extra.append(f"nurses {r['nurses_on_duty']:g}/{r['nurses_required']:g}")
            lines.append(
                f"{r['date']}: admissions {r['admissions']:g}, emergency {r['emergency_cases']:g}, "
                f"beds {_pct(r['bed_occupancy'])}, ICU {_pct(r['icu_occupancy'])}, "
                f"doctor load {r['doctor_workload']:g}" + (f", {', '.join(extra)}" if extra else "")
            )
        batches = sorted({str(r["batch_id"]) for r in items if r.get("batch_id")})
        chunks.append({
            "chunk_key": f"snap:{dept}:{year}-W{week:02d}",
            "doc_type": "snapshot_week",
            "title": f"{dept} · week of {start}",
            "content": summary + "\n" + "\n".join(lines),
            "department": dept,
            "date_start": start,
            "date_end": end,
            "batch_ids": ("," + ",".join(batches) + ",") if batches else None,
            "min_role": "Viewer",
        })
    return chunks


def _role_only(recorded_by: str) -> str:
    # "Dr. Sarah Chen (Chief Medical Officer)" -> "Chief Medical Officer"
    m = re.search(r"\(([^)]+)\)\s*$", recorded_by or "")
    return m.group(1) if m else "staff member"


def _decision_chunks(db) -> list[dict]:
    chunks = []
    for d in db.query(DecisionRecord).order_by(DecisionRecord.id.desc()).limit(500).all():
        day = d.timestamp.strftime("%Y-%m-%d") if d.timestamp else None
        chunks.append({
            "chunk_key": f"decision:{d.id}",
            "doc_type": "decision",
            "title": f"Decision #{d.id} · {day}",
            "content": scrub_text(
                f"Decision recorded {day} for {d.department} by a {_role_only(d.recorded_by)}. "
                f"Issue: {d.issue}. Recommendation: {d.recommendation}. Action taken: {d.administrator_action}. "
                f"Status: {d.outcome}. {d.outcome_details or ''}"
            ),
            "department": d.department,
            "date_start": day,
            "date_end": day,
            "min_role": "Viewer",
        })
    return chunks


def _event_chunks(db) -> list[dict]:
    chunks = []
    for e in db.query(HistoricalEvent).all():
        f = e.to_dict()["features"]
        chunks.append({
            "chunk_key": f"event:{e.id}",
            "doc_type": "event",
            "title": f"Past event · {e.date}",
            "content": (
                f"Historical event on {e.date} in {e.department}: {e.situation} "
                f"Bed occupancy {_pct(f['bed_occupancy'])}, ICU {_pct(f['icu_occupancy'])}, "
                f"admissions {f['admissions']:g}. Action taken: {e.previous_action} Outcome: {e.outcome} ({e.outcome_status})."
            ),
            "department": e.department,
            "date_start": e.date,
            "date_end": e.date,
            "min_role": "Viewer",
        })
    return chunks


def _alert_chunks(db) -> list[dict]:
    from app.services.state_service import compute_current_state  # avoid import cycle
    from app.services.alert_service import apply_state
    state = compute_current_state(db)
    chunks = []
    for a in apply_state(db, state["alerts"], include_all=True):
        chunks.append({
            "chunk_key": f"alert:{a['id']}",
            "doc_type": "alert",
            "title": f"Alert · {a['resource_type']} · {state['date']}",
            "content": (f"{a['severity'].title()} {a.get('kind', 'threshold')} alert for {a['resource_type']} on {state['date']} "
                        f"(status: {a['state']}). {a['reason']} Suggested action: {a['suggested_action']}"),
            "department": state["department"],
            "date_start": state["date"],
            "date_end": state["date"],
            "min_role": "Viewer",
        })
    return chunks


def _audit_chunks(db) -> list[dict]:
    """Daily activity digests (Admin-only). Chat questions are excluded."""
    since = datetime.now() - timedelta(days=30)
    rows = (db.query(AuditLog).filter(AuditLog.timestamp >= since, AuditLog.action != "chat_question")
            .order_by(AuditLog.timestamp.asc()).limit(2000).all())
    by_day = defaultdict(list)
    for r in rows:
        by_day[r.timestamp.strftime("%Y-%m-%d")].append(r)
    chunks = []
    for day, items in by_day.items():
        counts = Counter(i.action for i in items)
        lines = [f"{i.timestamp.strftime('%H:%M')} {i.username} ({i.role or '-'}) {i.action.replace('_', ' ')}"
                 f"{' ' + i.entity_type + ' #' + i.entity_id if i.entity_type and i.entity_id else ''}"
                 for i in items[-60:]]
        chunks.append({
            "chunk_key": f"audit:{day}",
            "doc_type": "audit",
            "title": f"Audit activity · {day}",
            "content": f"Audit log activity on {day}: " + ", ".join(f"{n} {a.replace('_', ' ')}" for a, n in counts.items())
                       + ".\n" + "\n".join(lines),
            "department": None,
            "date_start": day,
            "date_end": day,
            "min_role": "Admin",
        })
    return chunks


def _policy_chunks() -> list[dict]:
    chunks = []
    if not POLICY_DIR.exists():
        return chunks
    for path in sorted(POLICY_DIR.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)$", body, re.M)
        doc_title = title_match.group(1).strip() if title_match else path.stem
        sections = re.split(r"^##\s+", body, flags=re.M)
        intro = sections[0]
        for i, sec in enumerate(sections[1:] or [intro]):
            heading, _, content = sec.partition("\n")
            chunks.append({
                "chunk_key": f"policy:{path.stem}:{i}",
                "doc_type": "policy",
                "title": f"{doc_title} — {heading.strip()}" if sections[1:] else doc_title,
                "content": f"{doc_title}. {heading.strip()}.\n{content.strip()}",
                "department": None,
                "date_start": None,
                "date_end": None,
                "min_role": "Viewer",
            })
    return chunks


# ---- Store -------------------------------------------------------------------
def _pgvector_available() -> bool:
    if _state["pgvector"] is not None:
        return _state["pgvector"]
    ok = False
    if engine.dialect.name == "postgresql":
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.execute(text(f"ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector({EMBED_DIM})"))
            ok = True
        except Exception as exc:
            logger.info("pgvector unavailable (%s); using in-memory vector index.", exc)
    _state["pgvector"] = ok
    return ok


def _vec_literal(vec: np.ndarray) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def rebuild_index(db=None) -> dict:
    """Upsert every chunk; re-embed only chunks whose content changed."""
    own = db is None
    db = db or SessionLocal()
    try:
        with _lock:
            built = (_snapshot_chunks(db) + _decision_chunks(db) + _event_chunks(db)
                     + _alert_chunks(db) + _audit_chunks(db) + _policy_chunks())
            model_name = embedding_model_name()
            existing = {c.chunk_key: c for c in db.query(RagChunk).all()}
            wanted = {c["chunk_key"] for c in built}

            to_embed = []
            for c in built:
                c["content_hash"] = hashlib.sha256(c["content"].encode()).hexdigest()
                row = existing.get(c["chunk_key"])
                if not row or row.content_hash != c["content_hash"] or row.embedding_model != model_name:
                    to_embed.append(c)
                elif row.min_role != c["min_role"] or row.batch_ids != c.get("batch_ids"):
                    row.min_role, row.batch_ids = c["min_role"], c.get("batch_ids")

            vectors = embed([f"{c['title']}\n{c['content']}" for c in to_embed]) if to_embed else []
            pg = _pgvector_available()
            for c, vec in zip(to_embed, vectors):
                row = existing.get(c["chunk_key"]) or RagChunk(chunk_key=c["chunk_key"])
                for key in ("doc_type", "title", "content", "department", "date_start", "date_end", "min_role", "content_hash"):
                    setattr(row, key, c[key])
                row.batch_ids = c.get("batch_ids")
                row.embedding = json.dumps([round(float(x), 6) for x in vec])
                row.embedding_model = model_name
                db.add(row)
            removed = [k for k in existing if k not in wanted]
            if removed:
                db.query(RagChunk).filter(RagChunk.chunk_key.in_(removed)).delete(synchronize_session=False)
            db.commit()

            if pg and to_embed:
                with engine.begin() as conn:
                    for c, vec in zip(to_embed, vectors):
                        conn.execute(text("UPDATE rag_chunks SET embedding_vec = CAST(:v AS vector) WHERE chunk_key = :k"),
                                     {"v": _vec_literal(vec), "k": c["chunk_key"]})

            _state.update(dirty=False, matrix=None, rows=None, version=_state["version"] + 1)
            _cache.clear()
            return {"chunks": len(built), "embedded": len(to_embed), "removed": len(removed), "pgvector": pg}
    finally:
        if own:
            db.close()


def remove_batch(db, batch_id) -> int:
    """Drop chunks built from a rolled-back upload (rebuilt from active rows next)."""
    n = db.query(RagChunk).filter(RagChunk.batch_ids.like(f"%,{batch_id},%")).delete(synchronize_session=False)
    db.commit()
    return n


@data_events.subscribe
def _on_data_changed(db, reason: str, batch_id=None):
    with _lock:
        if reason == "rollback" and batch_id is not None:
            remove_batch(db, batch_id)
        _state["dirty"] = True
        _cache.clear()
    if reason in ("commit", "rollback"):
        rebuild_index(db)


def ensure_index(db) -> None:
    if _state["dirty"] or db.query(RagChunk.id).first() is None:
        rebuild_index(db)


def _load_memory(db):
    if _state["matrix"] is None:
        rows = db.query(RagChunk).all()
        mats = [np.asarray(json.loads(r.embedding), dtype=np.float32) if r.embedding else np.zeros(EMBED_DIM, np.float32)
                for r in rows]
        _state["rows"] = [{
            "key": r.chunk_key, "type": r.doc_type, "title": r.title, "content": r.content,
            "department": r.department, "date_start": r.date_start, "date_end": r.date_end,
            "min_role": r.min_role or "Viewer", "tokens": tokenize(r.title + " " + r.content),
        } for r in rows]
        _state["matrix"] = np.vstack(mats) if mats else np.zeros((0, EMBED_DIM), np.float32)
    return _state["rows"], _state["matrix"]


# ---- Query understanding -----------------------------------------------------
POLICY_WORDS = {"policy", "protocol", "sop", "procedure", "should", "guideline", "rule", "escalate", "escalation", "privacy"}
HISTORY_WORDS = {"last", "previous", "past", "history", "before", "compare", "week", "month", "trend", "happened"}
DECISION_WORDS = {"decision", "decided", "approved", "action", "actions", "taken", "dismissed"}
AUDIT_WORDS = {"audit", "who", "uploaded", "rolled", "rollback", "login", "logged"}


def parse_filters(question: str, departments: list[str]) -> dict:
    q = question.lower()
    filters = {}
    for d in departments:
        if d.lower() in q:
            filters["department"] = d
    m = re.findall(r"\d{4}-\d{2}-\d{2}", q)
    today = date.today()
    if m:
        filters["date_from"], filters["date_to"] = min(m), max(m)
    elif "last week" in q:
        filters["date_from"], filters["date_to"] = str(today - timedelta(days=13)), str(today - timedelta(days=7))
    elif "this week" in q:
        filters["date_from"], filters["date_to"] = str(today - timedelta(days=6)), str(today)
    elif "yesterday" in q:
        filters["date_from"] = filters["date_to"] = str(today - timedelta(days=1))
    return filters


def _bm25(query_tokens, rows, k1=1.4, b=0.75):
    n = len(rows)
    if not n or not query_tokens:
        return np.zeros(n)
    avgdl = sum(len(r["tokens"]) for r in rows) / n or 1
    df = Counter(t for r in rows for t in set(r["tokens"]))
    scores = np.zeros(n)
    for i, r in enumerate(rows):
        tf = Counter(r["tokens"])
        dl = len(r["tokens"]) or 1
        for t in query_tokens:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                scores[i] += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * dl / avgdl))
    return scores


def _overlaps(row, start, end) -> bool:
    if not row["date_start"]:
        return True  # undated (policies) always pass
    return not (row["date_end"] < start or row["date_start"] > end)


def retrieve(db, question: str, role: str = "Viewer", k: int = TOP_K, filters: dict | None = None) -> dict:
    """Hybrid retrieval with metadata and role filters, MMR rerank and caching."""
    ensure_index(db)
    filters = filters if filters is not None else parse_filters(question, snapshot_service.departments(db))
    key = (" ".join(tokenize(question)), role, json.dumps(filters, sort_keys=True), _state["version"], k)
    if key in _cache:
        _cache.move_to_end(key)
        return {**_cache[key], "cached": True}

    rows, matrix = _load_memory(db)
    allowed = ROLES.index(role) if role in ROLES else 0
    idx = [i for i, r in enumerate(rows) if ROLES.index(r["min_role"]) <= allowed]
    if "department" in filters:
        idx = [i for i in idx if rows[i]["department"] in (None, filters["department"])]
    if "date_from" in filters:
        idx = [i for i in idx if _overlaps(rows[i], filters["date_from"], filters["date_to"])]
    if not idx:
        result = {"chunks": [], "confidence": "low", "filters": filters}
        _cache[key] = result
        return result

    qvec = embed([question], input_type="query")[0]
    vec_scores = matrix[idx] @ qvec
    if _pgvector_available():
        try:  # use the database's ANN ordering when pgvector is present
            with engine.connect() as conn:
                res = conn.execute(text("SELECT chunk_key, 1 - (embedding_vec <=> CAST(:v AS vector)) AS sim FROM rag_chunks "
                                        "WHERE embedding_vec IS NOT NULL ORDER BY embedding_vec <=> CAST(:v AS vector) LIMIT 60"),
                                   {"v": _vec_literal(qvec)}).fetchall()
            sims = {r[0]: float(r[1]) for r in res}
            vec_scores = np.array([sims.get(rows[i]["key"], float(vec_scores[j])) for j, i in enumerate(idx)])
        except Exception as exc:
            logger.warning("pgvector search failed (%s); using in-memory scores.", exc)

    qtokens = tokenize(question)
    kw = _bm25(qtokens, [rows[i] for i in idx])
    kw_norm = kw / kw.max() if kw.max() > 0 else kw

    qset = set(qtokens)
    combined = []
    for j, i in enumerate(idx):
        r = rows[i]
        score = 0.55 * float(vec_scores[j]) + 0.45 * float(kw_norm[j])
        if r["type"] == "policy" and qset & POLICY_WORDS:
            score += 0.15
        if r["type"] == "snapshot_week" and qset & HISTORY_WORDS:
            score += 0.1
        if r["type"] == "decision" and qset & DECISION_WORDS:
            score += 0.15
        if r["type"] == "audit" and qset & AUDIT_WORDS:
            score += 0.15
        if r["type"] in ("snapshot_week", "decision", "alert") and r["date_end"]:
            age = (date.today() - date.fromisoformat(r["date_end"])).days
            score += 0.05 * math.exp(-max(age, 0) / 14)
        combined.append(score)
    combined = np.array(combined)

    # MMR: relevance minus redundancy with already-picked chunks.
    order = list(np.argsort(-combined)[: k * 4])
    picked = []
    while order and len(picked) < k:
        best, best_val = None, -1e9
        for j in order:
            redundancy = max((float(matrix[idx[j]] @ matrix[idx[p]]) for p in picked), default=0.0)
            val = 0.8 * combined[j] - 0.2 * redundancy
            if val > best_val:
                best, best_val = j, val
        picked.append(best)
        order.remove(best)

    chunks = [{
        "id": rows[idx[j]]["key"], "type": rows[idx[j]]["type"], "title": rows[idx[j]]["title"],
        "content": rows[idx[j]]["content"], "department": rows[idx[j]]["department"],
        "date_start": rows[idx[j]]["date_start"], "date_end": rows[idx[j]]["date_end"],
        "score": round(float(combined[j]), 3),
    } for j in picked]
    top = chunks[0]["score"] if chunks else 0
    confidence = "high" if top >= 0.55 else "medium" if top >= 0.3 else "low"
    result = {"chunks": chunks, "confidence": confidence, "filters": filters}
    _cache[key] = result
    if len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)
    return result
