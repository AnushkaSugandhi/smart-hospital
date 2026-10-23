"""Password hashing, signed tokens and role-based access dependencies.

Uses only the standard library so it runs on free-tier hosts without extra
packages. Tokens are HMAC-SHA256 signed and expire after TOKEN_TTL_HOURS.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger("smart_hospital.security")

ROLES = ["Viewer", "Analyst", "Admin"]  # ascending privilege
LEGACY_ROLE_MAP = {
    "Administrator": "Admin",
    "Chief Medical Officer": "Analyst",
    "Chief Operations Officer": "Admin",
}

TOKEN_TTL_HOURS = float(os.getenv("TOKEN_TTL_HOURS", "12"))
_SECRET = os.getenv("SECRET_KEY")
if not _SECRET:
    _SECRET = secrets.token_urlsafe(32)
    if os.getenv("ENVIRONMENT") == "production":
        logger.warning("SECRET_KEY is not set; generated a random key. Sessions reset on restart.")
SECRET_KEY = _SECRET.encode()

_PBKDF2_ITERATIONS = 200_000


def normalize_role(role: str | None) -> str:
    role = LEGACY_ROLE_MAP.get(role or "", role or "Viewer")
    return role if role in ROLES else "Viewer"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS).hex()
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt}${digest}"


def is_hashed(value: str | None) -> bool:
    return bool(value) and value.startswith("pbkdf2$")


def verify_password(password: str, stored: str) -> bool:
    if not is_hashed(stored):
        return False
    _, iterations, salt, digest = stored.split("$", 3)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(username: str, role: str, full_name: str = "") -> str:
    payload = {
        "sub": username,
        "role": normalize_role(role),
        "name": full_name,
        "exp": int(time.time() + TOKEN_TTL_HOURS * 3600),
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(SECRET_KEY, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(SECRET_KEY, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


@dataclass
class CurrentUser:
    username: str
    role: str
    full_name: str = ""
    ip_address: str | None = None

    def has_role(self, minimum: str) -> bool:
        return ROLES.index(self.role) >= ROLES.index(minimum)

    def to_dict(self) -> dict:
        return {"username": self.username, "role": self.role, "full_name": self.full_name}


def get_current_user(request: Request) -> CurrentUser:
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else ""
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CurrentUser(
        username=payload["sub"],
        role=normalize_role(payload.get("role")),
        full_name=payload.get("name", ""),
        ip_address=request.client.host if request.client else None,
    )


def require_role(minimum: str):
    """Dependency factory: reject users below `minimum` with 403."""
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_role(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the {minimum} role. You are signed in as {user.role}.",
            )
        return user
    return dependency


viewer = require_role("Viewer")
analyst = require_role("Analyst")
admin = require_role("Admin")
