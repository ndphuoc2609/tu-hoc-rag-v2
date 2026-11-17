"""Auth: pbkdf2_hmac stdlib + session token luu DB (khong JWT, khong passlib).

Token gui dang Bearer; server chi luu sha256 cua token, khong luu token tho.
ponytail: ceiling — session khong het han tu dong; muon het han / refresh
thi them expires_at vao bang sessions (upgrade path).
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import Header, HTTPException


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return f"pbkdf2$200000${salt}${dk.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, hexhash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt), int(iters))
        return secrets.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


def new_token() -> tuple[str, str]:
    """Tra (token tho gui client, sha256 luu DB)."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def get_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "chua dang nhap")
    return authorization[7:]


def public_user(row: dict) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"]}
