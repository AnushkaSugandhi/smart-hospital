"""Alerts (acknowledge/snooze), next-action recommendations and resources."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, analyst, viewer
from app.db.database import get_db
from app.db.models import AlertState, DecisionRecord
from app.services import audit_service
from app.services.alert_service import apply_state, set_state
from app.services.recommendation_service import next_actions
from app.services.state_service import compute_current_state

router = APIRouter(prefix="/api/v1", tags=["operations"])


class SnoozeRequest(BaseModel):
    minutes: int = Field(60, ge=5, le=24 * 60)


class AckRequest(BaseModel):
    note: Optional[str] = None


class RecommendationDecision(BaseModel):
    decision: Literal["approve", "dismiss"]
    note: Optional[str] = None


@router.get("/alerts")
def alerts(
    include_all: bool = False,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(viewer),
):
    """Active alerts (acknowledged and snoozed ones are hidden unless include_all)."""
    return apply_state(db, compute_current_state(db, department)["alerts"], include_all=include_all)


def _find_alert(db, alert_id: str) -> dict:
    for alert in compute_current_state(db)["alerts"]:
        if alert["id"] == alert_id:
            return alert
    raise HTTPException(404, "Alert not found or no longer active.")


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, payload: AckRequest = AckRequest(), db: Session = Depends(get_db),
                      user: CurrentUser = Depends(analyst)):
    alert = _find_alert(db, alert_id)
    state = set_state(db, alert_id, "acknowledged", user, note=payload.note)
    audit_service.record(db, user, "alert_acknowledge", "alert", alert_id,
                         {"severity": alert["severity"], "reason": alert["reason"], "note": payload.note})
    return {"status": "acknowledged", "state": state.to_dict()}


@router.post("/alerts/{alert_id}/snooze")
def snooze_alert(alert_id: str, payload: SnoozeRequest = SnoozeRequest(), db: Session = Depends(get_db),
                 user: CurrentUser = Depends(analyst)):
    alert = _find_alert(db, alert_id)
    state = set_state(db, alert_id, "snoozed", user, minutes=payload.minutes)
    audit_service.record(db, user, "alert_snooze", "alert", alert_id,
                         {"minutes": payload.minutes, "severity": alert["severity"]})
    return {"status": "snoozed", "state": state.to_dict()}


@router.get("/recommendations/next")
def recommended_actions(department: Optional[str] = None, db: Session = Depends(get_db),
                        user: CurrentUser = Depends(viewer)):
    """'What should I do now?': top 3 actions with why and simulated impact."""
    state = compute_current_state(db, department)
    actions = next_actions(state, state["alerts"], limit=5)
    handled = {s.item_id for s in db.query(AlertState).filter(
        AlertState.item_id.in_([a["id"] for a in actions])).all()} if actions else set()
    return [a for a in actions if a["id"] not in handled][:3]


@router.post("/recommendations/next/{rec_id}/decide")
def decide_recommendation(rec_id: str, payload: RecommendationDecision, db: Session = Depends(get_db),
                          user: CurrentUser = Depends(analyst)):
    state = compute_current_state(db)
    action = next((a for a in next_actions(state, state["alerts"], limit=5) if a["id"] == rec_id), None)
    if not action:
        raise HTTPException(404, "Recommendation not found or no longer relevant.")

    approved = payload.decision == "approve"
    decision = DecisionRecord(
        department=state["department"],
        issue=action["why"],
        recommendation=action["title"],
        administrator_action=(f"Approved: {action['title']}" if approved else f"Dismissed: {action['title']}")
        + (f" — {payload.note}" if payload.note else ""),
        outcome="pending" if approved else "dismissed",
        outcome_details=action["impact"],
        recorded_by=f"{user.full_name or user.username} ({user.role})",
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    set_state(db, rec_id, "approved" if approved else "dismissed", user, note=payload.note)
    audit_service.record(db, user, f"recommendation_{payload.decision}", "decision", decision.id,
                         {"recommendation": action["title"], "impact": action["impact"]})
    return {"status": "approved" if approved else "dismissed", "decision": decision.to_dict()}


@router.get("/resources")
def resources(department: Optional[str] = None, db: Session = Depends(get_db),
              user: CurrentUser = Depends(viewer)):
    return compute_current_state(db, department)["resources"]
