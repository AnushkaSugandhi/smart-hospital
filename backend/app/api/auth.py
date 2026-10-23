from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, ROLES, create_token, normalize_role, verify_password, viewer
from app.db.database import get_db
from app.db.models import User
from app.services import audit_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        audit_service.record(db, None, "login_failed", "user", payload.username,
                             {"ip": request.client.host if request.client else None},
                             username=payload.username[:100] or "anonymous")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    role = normalize_role(user.role)
    current = CurrentUser(user.username, role, user.full_name or "",
                          request.client.host if request.client else None)
    audit_service.record(db, current, "login", "user", user.username)
    return {
        "status": "authenticated",
        "token": create_token(user.username, role, user.full_name or ""),
        "user": {
            "username": user.username,
            "role": role,
            "full_name": user.full_name,
        },
    }


@router.get("/me")
def get_current_user(user: CurrentUser = Depends(viewer)):
    return {**user.to_dict(), "roles": ROLES}
