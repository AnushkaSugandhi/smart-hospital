"""'Ask Smart Hospital' chat: grounded answers from live tools + RAG.

Numbers come from tools that call the same services as the dashboard
(summary, forecast, simulation, alerts, period comparison). History,
decisions and policies come from rag_service. With an Anthropic key the
answer is written by Claude using tool calling; without one (or if the API
fails) a deterministic data-only answer is produced from the same tools, so
the feature keeps working on free-tier hosting and in tests.
"""
import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from collections import defaultdict, deque
from types import SimpleNamespace

from app.core.security import CurrentUser
from app.db.database import SessionLocal
from app.db.models import ChatMessage, ChatSession
from app.services import audit_service, rag_service, snapshot_service
from app.services.alert_service import apply_state, hours_until
from app.services.queries import forecast_payload, run_simulation_payload
from app.services.state_service import compute_current_state
from app.services.upload_service import scrub_text

logger = logging.getLogger("smart_hospital.chat")

LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-5-5")
LLM_EFFORT = os.getenv("LLM_EFFORT", "low")  # chat is latency-sensitive
MAX_TOOL_TURNS = 4
RATE_LIMIT_PER_MIN = int(os.getenv("CHAT_RATE_LIMIT_PER_MIN", "20"))
DISCLAIMER = "AI supports decisions and does not replace medical judgment."

SUGGESTIONS = [
    "How many ICU beds are free?",
    "Which department is most overloaded?",
    "When will ICU be full?",
    "Compare this week with last week",
    "What does our ICU surge protocol say?",
    "What if admissions rise by 20%?",
]


def llm_enabled() -> bool:
    provider = os.getenv("LLM_PROVIDER", "").lower()
    if provider == "offline":
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")) or provider == "anthropic"


# ---- Tools (real services, compact results) ----------------------------------
METRIC_LABELS = {"admissions": "admissions", "emergency_cases": "emergency cases", "bed_occupancy": "bed occupancy",
                 "icu_occupancy": "ICU occupancy", "doctor_workload": "doctor workload", "staff_workload": "staff workload"}
METRICS = ["admissions", "emergency_cases", "bed_occupancy", "icu_occupancy", "doctor_workload", "staff_workload"]
SIM_KEYS = ["admissions_change_pct", "emergency_cases_change_pct", "available_beds_change_pct",
            "icu_capacity_change_pct", "doctor_availability_change_pct", "staff_availability_change_pct"]


def _dept_arg(args, db):
    dept = args.get("department")
    return dept if dept and dept in snapshot_service.departments(db) else None


def _department_ranking(db):
    ranked = []
    for dept in snapshot_service.departments(db):
        st = compute_current_state(db, dept)
        ranked.append({"department": dept, "date": st["date"], "risk_score": st["risk"]["score"],
                       "risk_level": st["risk"]["level_label"], "top_driver": st["risk"]["top_driver"]})
    return sorted(ranked, key=lambda r: r["risk_score"], reverse=True)


def tool_dashboard(db, args):
    s = compute_current_state(db, _dept_arg(args, db))
    out = {
        "date": s["date"], "department": s["department"],
        "risk": {"score": s["risk"]["score"], "level": s["risk"]["level_label"],
                 "factors": {f["label"]: f["contribution"] for f in s["risk"]["breakdown"]}},
        "beds": {k: s["beds"][k] for k in ("occupied", "available", "total", "occupancy_pct", "status")},
        "icu": {k: s["icu"][k] for k in ("occupied", "available", "total", "occupancy_pct", "status")},
        "doctors": {"patients_per_doctor": s["doctors"]["average_patients_per_doctor"],
                    "overloaded_estimate": s["doctors"]["overloaded"], "total": s["doctors"]["total"],
                    "pressure_pct": s["doctors"]["pressure_pct"], "status": s["doctors"]["status"]},
        "emergency": {"active_cases": s["emergency"]["active_cases"], "ed_bays": s["emergency"]["capacity"],
                      "pressure_pct": s["emergency"]["pressure_pct"], "status": s["emergency"]["status"]},
        "change_vs_previous_day_pct": {k: v["change_pct"] for k, v in s["trends"].items()},
        "departments_ranked": _department_ranking(db),
        "resources": [{"name": r["label"], "summary": r["summary"], "status": r["status"], "warning": r.get("warning")}
                      for r in s["resources"] if r.get("available")],
    }
    chart = {"kind": "table", "title": f"Live status · {s['date']}", "columns": ["Measure", "Value", "Status"], "rows": [
        ["Bed occupancy", f"{s['beds']['occupancy_pct']}% ({s['beds']['available']} of {s['beds']['total']} free)", s["beds"]["status"]],
        ["ICU occupancy", f"{s['icu']['occupancy_pct']}% ({s['icu']['available']} of {s['icu']['total']} free)", s["icu"]["status"]],
        ["Doctor workload", f"{s['doctors']['average_patients_per_doctor']} patients per doctor", s["doctors"]["status"]],
        ["Emergency pressure", f"{s['emergency']['pressure_pct']}% ({s['emergency']['active_cases']} cases)", s["emergency"]["status"]],
        ["Resource risk", f"{s['risk']['score']} / 100 ({s['risk']['level_label']})", {"low": "normal", "medium": "warning"}.get(s["risk"]["level"], "critical")],
    ]}
    return out, {"chart": chart, "action": {"label": "Open Overview", "page": "overview", "params": {}},
                 "source": {"id": "live:dashboard", "type": "live", "title": f"Live dashboard · {s['date']}"}}


def tool_forecast(db, args):
    metric = args.get("metric") if args.get("metric") in METRICS else "icu_occupancy"
    horizon = int(args.get("horizon_days") or 7)
    f = forecast_payload(db, metric, horizon, _dept_arg(args, db))
    ratio = metric.endswith("occupancy")
    fmt = (lambda v: round(v * 100, 1)) if ratio else (lambda v: round(v, 2))
    out = {"metric": metric, "unit": "%" if ratio else "", "method": f["method"], "last_date": f["dates"][-1] if f["dates"] else None,
           "latest": fmt(f["historical"][-1]), "forecast_next_days": [fmt(v) for v in f["forecast"]]}
    if ratio:
        hrs = hours_until(f["historical"][-1], f["forecast"], 0.95)
        out["hours_until_95pct"] = hrs
        out["note"] = "95% occupancy is treated as full." + ("" if hrs is not None else f" Not reached within {f['horizon']} days.")
    series = [{"label": d[5:], "actual": fmt(v)} for d, v in zip(f["dates"][-10:], f["historical"][-10:])]
    series += [{"label": f"+{i + 1}d", "forecast": fmt(v)} for i, v in enumerate(f["forecast"])]
    if len(series) > len(f["forecast"]):
        series[len(series) - len(f["forecast"]) - 1]["forecast"] = series[len(series) - len(f["forecast"]) - 1]["actual"]
    label = METRIC_LABELS[metric]
    return out, {"chart": {"kind": "line", "title": f"{label[0].upper() + label[1:]} forecast", "unit": out["unit"], "series": series},
                 "action": {"label": "Open in Forecasting", "page": "forecast", "params": {"metric": metric, "horizon": f["horizon"]}},
                 "source": {"id": f"live:forecast:{metric}", "type": "live", "title": f"Live forecast · {label}"}}


def tool_simulation(db, args):
    params = {k: float(args.get(k) or 0) for k in SIM_KEYS}
    res = run_simulation_payload(db, SimpleNamespace(name="Chat scenario", department="Emergency", **params))
    b, sim = res["baseline"], res["simulated"]
    out = {"scenario": {k: v for k, v in params.items() if v}, "baseline": b,
           "simulated": {k: sim[k] for k in ("bed_occupancy_pct", "icu_occupancy_pct", "doctor_workload", "staff_workload",
                                              "emergency_pressure_pct", "risk_score", "risk_level_label")}}
    rows = [[label, f"{b[k]:.1f}{u}", f"{sim[k]:.1f}{u}"] for k, label, u in [
        ("bed_occupancy_pct", "Bed occupancy", "%"), ("icu_occupancy_pct", "ICU occupancy", "%"),
        ("doctor_workload", "Patients per doctor", ""), ("emergency_pressure_pct", "Emergency pressure", "%"),
        ("risk_score", "Risk score", "")]]
    return out, {"chart": {"kind": "table", "title": "Scenario vs today", "columns": ["Measure", "Today", "Scenario"], "rows": rows},
                 "action": {"label": "Run in Simulator", "page": "whatif", "params": {k: int(v) for k, v in params.items() if v}},
                 "source": {"id": "live:simulation", "type": "live", "title": "What-if simulation"}}


def tool_alerts(db, args):
    alerts = apply_state(db, compute_current_state(db)["alerts"], include_all=bool(args.get("include_handled")))
    out = [{"severity": a["severity"], "kind": a.get("kind"), "resource": a["resource_type"], "reason": a["reason"],
            "suggested_action": a["suggested_action"], "state": a["state"]} for a in alerts]
    return {"alerts": out, "count": len(out)}, {
        "source": {"id": "live:alerts", "type": "live", "title": f"Live alerts ({len(out)})"},
        "action": {"label": "Open Overview", "page": "overview", "params": {}}}


def tool_compare(db, args):
    days = max(1, min(int(args.get("days") or 7), 30))
    rows = snapshot_service.series(db, _dept_arg(args, db))
    cur, prev = rows[-days:], rows[-2 * days:-days]
    def avg(items, k):
        vals = [r[k] for r in items if r.get(k) is not None]
        return sum(vals) / len(vals) if vals else None
    table, out = [], {}
    for k, label, ratio in [("admissions", "Admissions per day", False), ("emergency_cases", "Emergency cases", False),
                            ("bed_occupancy", "Bed occupancy", True), ("icu_occupancy", "ICU occupancy", True),
                            ("doctor_workload", "Patients per doctor", False)]:
        a, b = avg(prev, k), avg(cur, k)
        if a is None or b is None:
            continue
        scale = 100 if ratio else 1
        change = round((b - a) / a * 100, 1) if a else 0.0
        out[k] = {"previous": round(a * scale, 1), "current": round(b * scale, 1), "change_pct": change}
        unit = "%" if ratio else ""
        table.append([label, f"{a * scale:.1f}{unit}", f"{b * scale:.1f}{unit}", f"{change:+.1f}%"])
    period = {"current": f"{cur[0]['date']} to {cur[-1]['date']}" if cur else None,
              "previous": f"{prev[0]['date']} to {prev[-1]['date']}" if prev else None}
    return {"period": period, "averages": out}, {
        "chart": {"kind": "table", "title": f"Last {days} days vs the {days} before", "columns": ["Measure", "Previous", "Current", "Change"], "rows": table},
        "source": {"id": f"live:compare:{days}", "type": "live", "title": f"Period comparison ({days} days)"}}


TOOL_FUNCS = {
    "get_dashboard_summary": tool_dashboard,
    "get_forecast": tool_forecast,
    "run_simulation": tool_simulation,
    "get_alerts": tool_alerts,
    "compare_periods": tool_compare,
}

_dept_prop = {"type": "string", "description": "Optional department name; omit for the whole hospital."}
TOOLS = [
    {"name": "get_dashboard_summary", "eager_input_streaming": True,
     "description": "Current live hospital status: beds, ICU, doctors, emergency pressure, risk score and breakdown, "
                    "change vs previous day and resource stock (ventilators, theatres, nurses, oxygen, blood). "
                    "Use for any question about current numbers or which area is most overloaded.",
     "input_schema": {"type": "object", "properties": {"department": _dept_prop}, "additionalProperties": False}},
    {"name": "get_forecast", "eager_input_streaming": True,
     "description": "Forecast a metric for the next days from the daily history. For occupancy metrics it also returns "
                    "hours_until_95pct (95% is treated as full). Use for 'when will X be full' and future demand.",
     "input_schema": {"type": "object", "properties": {
         "metric": {"type": "string", "enum": METRICS},
         "horizon_days": {"type": "integer", "minimum": 1, "maximum": 14},
         "department": _dept_prop}, "required": ["metric"], "additionalProperties": False}},
    {"name": "run_simulation", "eager_input_streaming": True,
     "description": "What-if scenario on today's baseline. Each field is a percent change (e.g. 20 for +20%). "
                    "Returns projected occupancy, workload and risk. Does not change anything in the hospital.",
     "input_schema": {"type": "object", "properties": {k: {"type": "number"} for k in SIM_KEYS}, "additionalProperties": False}},
    {"name": "get_alerts", "eager_input_streaming": True,
     "description": "Active alerts (threshold, predicted and low-stock) with reasons and suggested actions.",
     "input_schema": {"type": "object", "properties": {"include_handled": {"type": "boolean"}}, "additionalProperties": False}},
    {"name": "compare_periods", "eager_input_streaming": True,
     "description": "Compare average metrics for the most recent N days with the N days before (e.g. this week vs last week).",
     "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 30},
                                                       "department": _dept_prop}, "additionalProperties": False}},
]
_ALLOWED_ARGS = {t["name"]: set(t["input_schema"]["properties"]) for t in TOOLS}


def run_tool(db, name, args):
    """Validate model-supplied input before calling a real service."""
    if name not in TOOL_FUNCS:
        raise ValueError(f"Unknown tool {name}")
    if not isinstance(args, dict) or set(args) - _ALLOWED_ARGS[name]:
        raise ValueError("Invalid tool input")
    return TOOL_FUNCS[name](db, args)


SYSTEM_PROMPT = f"""You are "Ask Smart Hospital", the operations assistant for Vardhaman General Hospital's decision support system. You help administrators, analysts and coordinators understand capacity, workload, alerts, forecasts, past decisions and hospital policies.

How to answer:
- For any current number, forecast, alert or scenario, call a tool. Never estimate or invent numbers; tool results are the live system of record.
- For history, past decisions, past events, audit activity and policies, use the knowledge snippets in the user message (labelled [S1], [S2], ...).
- Answer only from tool results and snippets. If they do not contain the answer, say "I don't know based on the data available" and suggest where in the system to look. Do not guess.
- Cite snippets inline like [S2]. When you use a tool result, say it comes from live data.
- Lead with the direct answer in one or two sentences, then up to four short bullets if helpful. Always include units (%, patients per doctor, hours). Use plain language.
- Department names, dates and thresholds must match the data exactly. Thresholds: green below 70%, amber 70-85%, red above 85%.
- You support operational decisions. Do not give diagnosis or treatment advice for individual patients; say that clinical judgment rests with clinicians.
- The data contains no personal patient information; do not ask for any.

{DISCLAIMER}"""


# ---- Offline (data-only) answers ---------------------------------------------
def _find_pct(q):
    m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", q)
    return float(m.group(1)) if m else None


POLICY_Q = re.compile(r"policy|protocol|\bsops?\b|procedure|guideline|should (we|i)|what do we do|what to do|steps|escalat|privacy|who can")


def offline_plan(question: str) -> list[tuple[str, dict]]:
    q = question.lower()
    if POLICY_Q.search(q):
        return []  # answered from policies / records
    if re.search(r"\bwhat if\b|simulat|scenario", q) or (_find_pct(q) is not None and re.search(r"rise|increase|drop|fall|grow|more|less", q)):
        pct = _find_pct(q) or 20
        if re.search(r"drop|fall|less|fewer|decrease", q):
            pct = -abs(pct)
        key = "admissions_change_pct"
        if "emergency" in q:
            key = "emergency_cases_change_pct"
        elif "doctor" in q:
            key = "doctor_availability_change_pct"
        elif "staff" in q or "nurse" in q:
            key = "staff_availability_change_pct"
        return [("run_simulation", {key: pct})]
    if "compare" in q or ("this week" in q and "last week" in q):
        return [("compare_periods", {"days": 7})]
    if re.search(r"\bfull\b|forecast|next week|run out|\breach|predict|tomorrow", q):
        metric = "bed_occupancy" if re.search(r"\bbed", q) and "icu" not in q else "icu_occupancy"
        if "admission" in q:
            metric = "admissions"
        return [("get_forecast", {"metric": metric, "horizon_days": 7})]
    if "alert" in q or "warning" in q:
        return [("get_alerts", {})]
    if re.search(r"icu|bed|free|available|overload|busiest|pressure|risk|doctor|emergency|ventilator|oxygen|blood|nurse|theatre|now|today|current", q) \
            and not re.search(r"policy|protocol|sop|procedure|should we|decision|decided|last month|history|happened|audit", q):
        return [("get_dashboard_summary", {})]
    return []


def _status_word(s):
    return {"normal": "normal", "warning": "elevated", "critical": "critical"}.get(s, s)


def _snippet_summary(s: dict, limit: int = 260) -> str:
    body = s["content"]
    if s["type"] == "policy":
        body = body.split("\n", 1)[-1]  # drop the "Title. Heading." line
        body = re.sub(r"^\s*(?:\d+\.|-)\s*", "", body, flags=re.M).replace("\n", " ")
        text = f"{s['title']}: {body}"
    else:
        text = " ".join(re.split(r"(?<=\.)\s", body.replace("\n", " "), maxsplit=2)[:2])
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def offline_answer(question: str, results: list[tuple[str, dict]], snippets: list[dict], confidence: str = "medium") -> str:
    q = question.lower()
    parts = []
    for name, out in results:
        if name == "get_dashboard_summary":
            if "icu" in q and re.search(r"free|available|bed", q):
                i = out["icu"]
                parts.append(f"**{i['available']} of {i['total']} ICU beds are free** ({i['occupancy_pct']}% occupied, {_status_word(i['status'])}), "
                             f"according to live data for {out['date']}.")
            elif re.search(r"overload|busiest|most|pressure", q):
                ranked = out["departments_ranked"]
                top = max(out["risk"]["factors"].items(), key=lambda kv: kv[1])
                if len(ranked) > 1:
                    lead = ranked[0]
                    parts.append(f"**{lead['department']} is the most overloaded department** (risk {lead['risk_score']}/100, "
                                 f"{lead['risk_level']}; main driver: {lead['top_driver']}). Next: "
                                 + ", ".join(f"{r['department']} {r['risk_score']}" for r in ranked[1:4]) + ".")
                else:
                    parts.append(f"Only **{out['department']}** has data loaded, so departments can't be compared yet. "
                                 f"Within it, the biggest pressure is **{top[0]}**, adding {top[1]} points to a risk score of "
                                 f"{out['risk']['score']}/100 ({out['risk']['level']}).")
                parts.append(f"- Emergency: {out['emergency']['pressure_pct']}% of {out['emergency']['ed_bays']} ED bays in use\n"
                             f"- Beds: {out['beds']['occupancy_pct']}% occupied\n- ICU: {out['icu']['occupancy_pct']}% occupied\n"
                             f"- Doctors: {out['doctors']['patients_per_doctor']} patients per doctor (about {out['doctors']['overloaded_estimate']} of {out['doctors']['total']} overloaded)")
            else:
                parts.append(f"Live status for {out['date']} ({out['department']}): risk {out['risk']['score']}/100 ({out['risk']['level']}). "
                             f"Beds {out['beds']['occupancy_pct']}% ({out['beds']['available']} free), ICU {out['icu']['occupancy_pct']}% "
                             f"({out['icu']['available']} free), emergency pressure {out['emergency']['pressure_pct']}%, "
                             f"{out['doctors']['patients_per_doctor']} patients per doctor.")
                warn = [r["warning"] for r in out["resources"] if r.get("warning")]
                if warn:
                    parts.append("Stock warnings: " + "; ".join(warn) + ".")
        elif name == "get_forecast":
            label = METRIC_LABELS[out["metric"]]
            if out.get("hours_until_95pct") is not None:
                h = out["hours_until_95pct"]
                when = f"about {round(h)} hours" if h < 36 else f"about {round(h / 24, 1):g} days"
                parts.append(f"**{label[0].upper() + label[1:]} is forecast to reach 95% (treated as full) in {when}.** It is {out['latest']}% now.")
            elif out["unit"] == "%":
                parts.append(f"**{label[0].upper() + label[1:]} is not forecast to reach 95% in the next {len(out['forecast_next_days'])} days.** "
                             f"It is {out['latest']}% now; the forecast peaks at {max(out['forecast_next_days'])}%.")
            else:
                parts.append(f"{label[0].upper() + label[1:]} is {out['latest']} now; next {len(out['forecast_next_days'])} days: "
                             + ", ".join(str(v) for v in out["forecast_next_days"]) + ".")
            parts.append(f"Method: {out['method'].replace('_', ' ')} on daily history.")
        elif name == "run_simulation":
            sim, b = out["simulated"], out["baseline"]
            change = ", ".join(f"{k.replace('_change_pct', '').replace('_', ' ')} {v:+g}%" for k, v in out["scenario"].items()) or "no change"
            parts.append(f"With {change}, the risk score would move from **{b['risk_score']} to {sim['risk_score']}** ({sim['risk_level_label']}). "
                         f"Beds {sim['bed_occupancy_pct']}%, ICU {sim['icu_occupancy_pct']}%, {sim['doctor_workload']} patients per doctor. "
                         "This is an estimate; nothing in the hospital changes.")
        elif name == "get_alerts":
            if not out["alerts"]:
                parts.append("There are no active alerts right now.")
            else:
                parts.append(f"There are **{out['count']} active alerts**:")
                parts.append("\n".join(f"- {a['severity'].title()} · {a['resource']}: {a['reason'].split('. ')[0]}. "
                                       f"Suggested: {a['suggested_action']}" for a in out["alerts"][:5]))
        elif name == "compare_periods":
            avg = out["averages"]
            parts.append(f"Last 7 days ({out['period']['current']}) vs the 7 days before ({out['period']['previous']}):")
            parts.append("\n".join(f"- {METRIC_LABELS[k][0].upper() + METRIC_LABELS[k][1:]}: {v['previous']} → {v['current']} ({v['change_pct']:+.1f}%)"
                                   for k, v in avg.items()))
    if not results:
        if snippets and confidence != "low":
            parts.append("Here is what I found in hospital records:")
            parts.append("\n".join(f"- {_snippet_summary(s)} [S{i}]" for i, s in enumerate(snippets[:3], 1)))
        else:
            parts.append("I don't know based on the data available. Try the Overview or Forecasting pages, or rephrase the question.")
    return "\n\n".join(parts)


# ---- Rate limiting -----------------------------------------------------------
_recent = defaultdict(deque)


def rate_limited(username: str) -> bool:
    now = time.time()
    q = _recent[username]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MIN:
        return True
    q.append(now)
    return False


# ---- Streaming ---------------------------------------------------------------
def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _context_block(snippets):
    if not snippets:
        return "<knowledge>\n(no matching records)\n</knowledge>"
    lines = []
    for i, s in enumerate(snippets, 1):
        when = f"{s['date_start']}..{s['date_end']}" if s.get("date_start") else "undated"
        lines.append(f"[S{i}] {s['type']} | {s['title']} | {when}\n{s['content']}")
    return "<knowledge>\n" + "\n\n".join(lines) + "\n</knowledge>"


async def _stream_text(text: str):
    # Word-sized chunks so the UI typing animation looks natural.
    for piece in re.findall(r"\S+\s*|\n", text):
        yield piece
        await asyncio.sleep(0.008)


def _history(db, session_id, limit=6):
    rows = (db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc()).limit(limit).all())
    msgs = [{"role": r.role, "content": r.content} for r in reversed(rows)]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


async def answer_stream(user: CurrentUser, question: str, session_id: str | None):
    """Yields SSE strings. Uses its own DB session (outlives the request scope)."""
    db = SessionLocal()
    started = time.time()
    try:
        question = scrub_text(question.strip())[:2000]
        session = db.get(ChatSession, session_id) if session_id else None
        if session and session.username != user.username:
            session = None
        if not session:
            session = ChatSession(id=uuid.uuid4().hex, username=user.username, title=question[:80] or "New chat")
            db.add(session)
            db.commit()
        history = _history(db, session.id)
        db.add(ChatMessage(session_id=session.id, role="user", content=question))
        db.commit()
        audit_service.record(db, user, "chat_question", "chat_session", session.id, {"question": question[:500]})

        mode = "llm" if llm_enabled() else "offline"
        yield sse("meta", {"session_id": session.id, "mode": mode, "disclaimer": DISCLAIMER})
        yield sse("status", {"text": "Searching hospital records…"})

        try:
            retrieval = await asyncio.to_thread(rag_service.retrieve, db, question, user.role)
        except Exception as exc:
            logger.warning("Retrieval failed: %s", exc)
            retrieval = {"chunks": [], "confidence": "low"}
            yield sse("status", {"text": "Records search is unavailable; answering from live data only."})
        snippets = retrieval["chunks"]

        charts, actions, live_sources, answer = [], [], [], ""
        used_tools = []

        if mode == "llm":
            try:
                async for kind, payload in _llm_answer(db, question, history, snippets):
                    if kind == "token":
                        answer += payload
                        yield sse("token", {"text": payload})
                    elif kind == "status":
                        yield sse("status", {"text": payload})
                    elif kind == "tool":
                        used_tools.append(payload["name"])
                        extras = payload["extras"]
                        if extras.get("chart"):
                            charts.append(extras["chart"]); yield sse("chart", extras["chart"])
                        if extras.get("action"):
                            actions.append(extras["action"])
                        live_sources.append(extras["source"])
            except Exception as exc:
                logger.warning("LLM answer failed, using data-only answer: %s", exc)
                if not answer:
                    mode = "offline"
                    yield sse("status", {"text": "The AI writer is unavailable right now, so here is a data-only answer."})
                else:
                    yield sse("token", {"text": "\n\n(The answer was interrupted. Please try again.)"})

        if mode == "offline":
            results = []
            for name, args in offline_plan(question):
                yield sse("status", {"text": f"Checking live data: {name.replace('_', ' ')}…"})
                try:
                    out, extras = await asyncio.to_thread(run_tool, db, name, args)
                except Exception as exc:
                    logger.warning("Tool %s failed: %s", name, exc)
                    continue
                used_tools.append(name)
                results.append((name, out))
                if extras.get("chart"):
                    charts.append(extras["chart"]); yield sse("chart", extras["chart"])
                if extras.get("action"):
                    actions.append(extras["action"])
                live_sources.append(extras["source"])
            answer = offline_answer(question, results, snippets, retrieval["confidence"])
            async for piece in _stream_text(answer):
                yield sse("token", {"text": piece})

        cited = {int(n) for n in re.findall(r"\[S(\d+)\]", answer)}
        doc_sources = [{**{k: s[k] for k in ("id", "type", "title", "department", "date_start", "date_end", "score")}, "ref": f"S{i}"}
                       for i, s in enumerate(snippets, 1) if i in cited or (not cited and not used_tools and i <= 3)]
        sources = live_sources + doc_sources
        if used_tools:
            confidence = "high"
        elif not doc_sources or retrieval["confidence"] == "low" or "don't know" in answer.lower():
            confidence = "low"
        else:
            confidence = retrieval["confidence"]
        extras = {"sources": sources, "charts": charts, "actions": actions, "confidence": confidence, "mode": mode,
                  "latency_ms": int((time.time() - started) * 1000)}
        msg = ChatMessage(session_id=session.id, role="assistant", content=answer or "(no answer)", extras=json.dumps(extras, default=str))
        db.add(msg)
        session.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
        yield sse("done", {"message_id": msg.id, **extras})
    except Exception as exc:
        logger.exception("Chat failed: %s", exc)
        yield sse("error", {"message": "Sorry, something went wrong while answering. Please try again in a moment."})
    finally:
        db.close()


async def _llm_answer(db, question, history, snippets):
    """Claude tool loop with streaming. Yields ("token"|"status"|"tool", payload)."""
    import anthropic

    client = anthropic.AsyncAnthropic(timeout=60.0, max_retries=1)
    messages = history + [{"role": "user", "content": f"{_context_block(snippets)}\n\nQuestion: {question}"}]
    json_retries = 0

    for _turn in range(MAX_TOOL_TURNS + 1):
        try:
            async with client.beta.messages.stream(
                model=LLM_MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": LLM_EFFORT},
                cache_control={"type": "ephemeral"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield "token", event.text
                    elif event.type == "content_block_start" and getattr(event.content_block, "type", "") == "tool_use":
                        yield "status", f"Checking live data: {event.content_block.name.replace('_', ' ')}…"
                response = await stream.get_final_message()
            json_retries = 0
        except ValueError:
            json_retries += 1  # unparseable streamed tool input; re-issue the turn
            if json_retries > 2:
                raise
            continue

        if response.stop_reason == "refusal":
            yield "token", "\n\nI can't help with that request. I can answer questions about hospital capacity, alerts, forecasts, decisions and policies."
            return
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            return
        if response.stop_reason == "max_tokens":
            yield "token", "\n\n(The answer was cut short.)"
            return

        results = []
        for block in tool_uses:
            try:
                out, extras = await asyncio.to_thread(run_tool, db, block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, default=str)})
                yield "tool", {"name": block.name, "extras": extras}
            except Exception as exc:
                results.append({"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                                "content": f"Tool failed: {exc}"})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})

    yield "token", "\n\n(I stopped after several data lookups. Try a more specific question.)"
