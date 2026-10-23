import io
import json
import os

os.environ["LLM_PROVIDER"] = "offline"  # deterministic, no API key needed

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.db.models import RagChunk
from app.main import app
from app.services import chat_service, rag_service

client = TestClient(app)


def auth(username, password):
    token = client.post("/api/v1/auth/login", json={"username": username, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


ADMIN, VIEWER = auth("admin", "admin123"), auth("viewer", "viewer123")


def ask(question, headers=VIEWER, session_id=None):
    events, current = [], None
    with client.stream("POST", "/api/v1/chat", json={"message": question, "session_id": session_id}, headers=headers) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            if line.startswith("event:"):
                current = line[7:]
            elif line.startswith("data:"):
                events.append((current, json.loads(line[5:])))
    text = "".join(d["text"] for e, d in events if e == "token")
    done = next(d for e, d in events if e == "done")
    meta = next(d for e, d in events if e == "meta")
    return text, done, meta, events


def test_chat_requires_login():
    assert client.post("/api/v1/chat", json={"message": "hi"}).status_code == 401


def test_icu_question_uses_live_numbers_not_guesses():
    summary = client.get("/api/v1/dashboard/summary", headers=VIEWER).json()
    text, done, _, events = ask("How many ICU beds are free?")
    assert f"{summary['icu']['available']} of {summary['icu']['total']} ICU beds are free" in text
    assert any(s["type"] == "live" for s in done["sources"])
    assert done["confidence"] == "high"
    assert [e for e, _ in events].index("token") > 0  # status/meta stream before the answer
    assert any(e == "chart" for e, _ in events)


def test_forecast_question_returns_chart_and_action():
    text, done, _, _ = ask("When will ICU be full?")
    assert "ICU occupancy" in text and "95%" in text
    assert done["charts"][0]["kind"] == "line"
    assert done["actions"][0]["page"] == "forecast"


def test_simulation_question_links_to_simulator():
    _, done, _, _ = ask("What if admissions rise by 20%?")
    action = done["actions"][0]
    assert action["page"] == "whatif" and action["params"]["admissions_change_pct"] == 20


def test_policy_question_is_answered_from_documents_with_citations():
    text, done, _, _ = ask("What does our ICU surge protocol say?")
    assert "[S1]" in text
    assert any(s["type"] == "policy" for s in done["sources"])


def test_unknown_question_says_i_dont_know_with_low_confidence():
    text, done, _, _ = ask("What is the capital of France?")
    assert "don't know" in text.lower()
    assert done["confidence"] == "low"


def test_history_feedback_and_audit():
    _, done, meta, _ = ask("Compare this week with last week")
    sid = meta["session_id"]
    ask("And which alerts are active?", session_id=sid)
    sessions = client.get("/api/v1/chat/sessions", headers=VIEWER).json()
    assert any(s["id"] == sid for s in sessions)
    msgs = client.get(f"/api/v1/chat/sessions/{sid}", headers=VIEWER).json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    assert client.post(f"/api/v1/chat/messages/{done['message_id']}/feedback", json={"value": "up"}, headers=VIEWER).json()["feedback"] == "up"
    # other users cannot read or rate this chat
    assert client.get(f"/api/v1/chat/sessions/{sid}", headers=ADMIN).status_code == 404
    log = client.get("/api/v1/audit?action=chat_question&username=viewer", headers=ADMIN).json()
    assert log["total"] >= 2


def test_audit_knowledge_is_admin_only():
    rag_service.rebuild_index()
    with SessionLocal() as db:
        viewer_hits = rag_service.retrieve(db, "audit log activity login", role="Viewer")["chunks"]
        admin_hits = rag_service.retrieve(db, "audit log activity login", role="Admin")["chunks"]
    assert not any(c["type"] == "audit" for c in viewer_hits)
    assert any(c["type"] == "audit" for c in admin_hits)


def test_index_is_anonymised():
    client.post("/api/v1/decisions", headers=ADMIN, json={
        "issue": "Call 98765 43210 re ICU", "recommendation": "r", "administrator_action": "a",
        "recorded_by": "Dr. Jane Roe (Chief Medical Officer)"})
    rag_service.rebuild_index()
    with SessionLocal() as db:
        content = " ".join(c.content for c in db.query(RagChunk).filter(RagChunk.doc_type == "decision").all())
    assert "98765 43210" not in content and "Jane Roe" not in content


def test_rollback_removes_rows_from_index():
    csv = ("date,department,admissions,emergency_cases,bed_occupancy,icu_occupancy,doctor_workload,staff_workload\n"
           "2026-01-05,IndexTest,40,5,0.9,0.9,12,9\n")
    res = client.post("/api/v1/uploads/commit", files={"file": ("i.csv", io.BytesIO(csv.encode()), "text/csv")}, headers=ADMIN).json()
    with SessionLocal() as db:
        assert db.query(RagChunk).filter(RagChunk.department == "IndexTest").count() == 1
    client.post(f"/api/v1/uploads/batches/{res['batch_id']}/rollback", headers=ADMIN)
    with SessionLocal() as db:
        assert db.query(RagChunk).filter(RagChunk.department == "IndexTest").count() == 0
        assert db.query(RagChunk).filter(RagChunk.batch_ids.like(f"%,{res['batch_id']},%")).count() == 0


def test_retrieval_cache_and_filters():
    with SessionLocal() as db:
        first = rag_service.retrieve(db, "bed occupancy last week", role="Viewer")
        second = rag_service.retrieve(db, "bed occupancy last week", role="Viewer")
    assert second.get("cached") and "date_from" in first["filters"]


def test_tool_input_is_validated():
    with SessionLocal() as db:
        try:
            chat_service.run_tool(db, "get_forecast", {"metric": "icu_occupancy", "drop_table": True})
            assert False, "unexpected argument should be rejected"
        except ValueError:
            pass


def test_series_matches_card_percentages():
    summary = client.get("/api/v1/dashboard/summary", headers=VIEWER).json()
    history = client.get("/api/v1/resources/history", headers=VIEWER).json()
    assert round(history[-1]["icu_occupancy"] * 100, 1) == summary["icu"]["occupancy_pct"]
    assert round(history[-1]["bed_occupancy"] * 100, 1) == summary["beds"]["occupancy_pct"]


# ---- Claude tool loop (fake streaming client; no network) ---------------------
class _FakeStream:
    def __init__(self, events, final):
        self._events, self._final = events, final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        async def gen():
            for e in self._events:
                yield e
        return gen()

    async def get_final_message(self):
        return self._final


def test_llm_tool_loop(monkeypatch):
    from types import SimpleNamespace as NS
    import anthropic

    calls = []
    tool_block = NS(type="tool_use", id="tu_1", name="get_dashboard_summary", input={})
    turns = [
        _FakeStream([NS(type="content_block_start", content_block=tool_block)],
                    NS(stop_reason="tool_use", content=[tool_block])),
        _FakeStream([NS(type="text", text="5 ICU beds are free "), NS(type="text", text="(live data).")],
                    NS(stop_reason="end_turn", content=[NS(type="text", text="5 ICU beds are free (live data).")])),
    ]

    class FakeClient:
        def __init__(self, **kw):
            self.beta = NS(messages=NS(stream=self.stream))

        def stream(self, **kw):
            calls.append({**kw, "messages": list(kw["messages"])})
            return turns[len(calls) - 1]

    monkeypatch.setattr(anthropic, "AsyncAnthropic", FakeClient)
    monkeypatch.setattr(chat_service, "llm_enabled", lambda: True)

    text, done, meta, events = ask("How many ICU beds are free?")
    assert meta["mode"] == "llm"
    assert text == "5 ICU beds are free (live data)."
    assert done["charts"] and done["sources"][0]["type"] == "live"

    first, second = calls
    assert first["model"] == chat_service.LLM_MODEL and first["fallbacks"] == "default"
    assert first["output_config"] == {"effort": chat_service.LLM_EFFORT}
    assert "tool_choice" not in first  # forced tool choice is rejected on current models
    assert {t["name"] for t in first["tools"]} == set(chat_service.TOOL_FUNCS)
    assert "<knowledge>" in first["messages"][-1]["content"]
    tool_result = second["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and tool_result["tool_use_id"] == "tu_1"
    assert json.loads(tool_result["content"])["icu"]["total"] == 20


def test_llm_failure_falls_back_to_data_only_answer(monkeypatch):
    import anthropic

    class Broken:
        def __init__(self, **kw):
            raise anthropic.APIConnectionError(request=None)

    monkeypatch.setattr(anthropic, "AsyncAnthropic", Broken)
    monkeypatch.setattr(chat_service, "llm_enabled", lambda: True)
    text, done, _, events = ask("How many ICU beds are free?")
    assert "ICU beds are free" in text and done["mode"] == "offline"
    assert any(e == "status" and "unavailable" in d["text"] for e, d in events)
