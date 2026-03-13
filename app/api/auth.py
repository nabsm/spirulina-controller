from __future__ import annotations

import logging
import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel

from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")

COOKIE_NAME = "spirulina_auth"
COOKIE_MAX_AGE = 7 * 24 * 3600  # 7 days

# Rate limiting: track failed attempts per IP
_failed_attempts: dict[str, list[float]] = defaultdict(list)
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300  # 5 minutes


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.auth_secret_key)


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}


def _client_ip(request: Request) -> str:
    if not request.client:
        return "unknown"
    # Only trust X-Forwarded-For when the direct connection is from a local reverse proxy
    if request.client.host in _TRUSTED_PROXIES:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Rightmost entry is the one added by our trusted proxy
            return forwarded.split(",")[-1].strip()
    return request.client.host


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    # Prune old entries
    _failed_attempts[ip] = [t for t in _failed_attempts[ip] if now - t < WINDOW_SECONDS]
    return len(_failed_attempts[ip]) >= MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    _failed_attempts[ip].append(time.monotonic())


def _clear_failures(ip: str) -> None:
    _failed_attempts.pop(ip, None)


def verify_cookie(request: Request) -> bool:
    """Check if request has a valid auth cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _get_serializer().loads(token, max_age=COOKIE_MAX_AGE)
        return data == "authenticated"
    except (BadSignature, SignatureExpired):
        return False


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    ip = _client_ip(request)

    if _is_rate_limited(ip):
        logger.warning("Rate limited login attempt from %s", ip)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many attempts. Try again later."},
        )

    if not secrets.compare_digest(req.password, settings.access_password):
        _record_failure(ip)
        remaining = MAX_ATTEMPTS - len(_failed_attempts[ip])
        logger.warning("Failed login from %s (%d attempts remaining)", ip, max(remaining, 0))
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid password"},
        )

    _clear_failures(ip)
    token = _get_serializer().dumps("authenticated")

    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=False,  # Set True if using HTTPS
    )
    logger.info("Successful login from %s", ip)
    return response


@router.get("/check")
async def check_auth(request: Request):
    if verify_cookie(request):
        return {"authenticated": True}
    return JSONResponse(status_code=401, content={"authenticated": False})


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(key=COOKIE_NAME)
    return response
