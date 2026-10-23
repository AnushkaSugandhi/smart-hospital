"""Ask Smart Hospital: streaming chat, history and feedback."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, admin, viewer
from app.db.database import get_db
from app.db.models import ChatMessage, ChatSession
from app.services import chat_service, rag_service

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    value: Optional[Literal["up", "down"]] = None


@router.post("/chat")
async def chat(payload: ChatRequest, user: CurrentUser = Depends(viewer)):
    """Server-sent events: meta, status, token, chart, done (or error)."""
    if chat_service.rate_limited(user.username):
        raise HTTPException(429, "You're asking questions very quickly. Please wait a moment and try again.")
    return StreamingResponse(
        chat_service.answer_stream(user, payload.message, payload.session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/suggestions")
def suggestions(user: CurrentUser = Depends(viewer)):
    return {"suggestions": chat_service.SUGGESTIONS, "disclaimer": chat_service.DISCLAIMER,
            "mode": "llm" if chat_service.llm_enabled() else "offline"}


@router.get("/chat/sessions")
def list_sessions(db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    rows = (db.query(ChatSession).filter(ChatSession.username == user.username)
            .order_by(ChatSession.updated_at.desc()).limit(50).all())
    return [r.to_dict() for r in rows]


def _own_session(db, session_id, user) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if not session or session.username != user.username:
        raise HTTPException(404, "Chat not found.")
    return session


@router.get("/chat/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    session = _own_session(db, session_id, user)
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc()).all()
    return {"session": session.to_dict(), "messages": [m.to_dict() for m in msgs]}


@router.delete("/chat/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), user: CurrentUser = Depends(viewer)):
    session = _own_session(db, session_id, user)
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"status": "deleted"}


@router.post("/chat/messages/{message_id}/feedback")
def feedback(message_id: int, payload: FeedbackRequest, db: Session = Depends(get_db),
             user: CurrentUser = Depends(viewer)):
    msg = db.get(ChatMessage, message_id)
    if not msg or msg.role != "assistant":
        raise HTTPException(404, "Message not found.")
    _own_session(db, msg.session_id, user)
    msg.feedback = payload.value
    db.commit()
    return {"status": "saved", "feedback": msg.feedback}


@router.post("/chat/reindex")
def reindex(db: Session = Depends(get_db), user: CurrentUser = Depends(admin)):
    """Rebuild the knowledge index (normally automatic after uploads)."""
    return rag_service.rebuild_index(db)
