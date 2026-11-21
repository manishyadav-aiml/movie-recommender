"""Security helpers: validation, rate limiting, CSRF, headers."""
from __future__ import annotations

import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from functools import wraps
from urllib.parse import urlparse

from flask import jsonify, request, session

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
UTM_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,60}$")


class ValidationError(ValueError):
    """Raised for bad user input. The message is safe to show to the user."""


# ------------------------------------------------------------------ validation
def clean_text(value, field: str, min_len: int = 0, max_len: int = 200) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be text.")
    value = _CONTROL.sub("", value).strip()
    if len(value) < min_len:
        raise ValidationError(f"{field} must be at least {min_len} characters.")
    if len(value) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters.")
    return value


def int_param(raw, field: str, default: int, lo: int, hi: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a whole number.")
    if not lo <= value <= hi:
        raise ValidationError(f"{field} must be between {lo} and {hi}.")
    return value


def rating_param(raw, title: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"Rating for '{title[:40]}' must be a number.")
    if not 0.5 <= value <= 5.0:
        raise ValidationError("Ratings must be between 0.5 and 5.")
    return value


# --------------------------------------------------------------- rate limiting
class RateLimiter:
    """Sliding-window limiter kept in memory (use Redis when running several workers)."""

    def __init__(self):
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)

    def allow(self, bucket: str, key: str, max_calls: int, window: int) -> bool:
        now = time.monotonic()
        q = self._hits[(bucket, key)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= max_calls:
            return False
        q.append(now)
        return True

    def limit(self, bucket: str, max_calls: int, window: int):
        def deco(fn):
            @wraps(fn)
            def wrapper(*a, **kw):
                if not self.allow(bucket, request.remote_addr or "unknown", max_calls, window):
                    resp = jsonify(error="Too many requests. Please slow down and try again later.")
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(window)
                    return resp
                return fn(*a, **kw)
            return wrapper
        return deco


# ------------------------------------------------------------------------ CSRF
def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def csrf_valid() -> bool:
    sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
    expected = session.get("csrf", "")
    return bool(expected) and hmac.compare_digest(str(sent), expected)


def origin_allowed(allowed: set[str]) -> bool:
    """Reject cross-site POSTs: Origin (when present) must be this host or whitelisted."""
    origin = request.headers.get("Origin")
    if not origin:
        return True
    return urlparse(origin).netloc == request.host or origin in allowed


# --------------------------------------------------------------------- headers
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
       "form-action 'self'; frame-ancestors 'none'")


def apply_security_headers(resp, production: bool, allowed_origins: set[str]):
    h = resp.headers
    h["Content-Security-Policy"] = CSP
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    if production:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith(("/api", "/admin")):
        h["Cache-Control"] = "no-store"
    # CORS is off by default (same-origin only). Only exact whitelisted origins are echoed.
    origin = request.headers.get("Origin")
    if origin and origin in allowed_origins:
        h["Access-Control-Allow-Origin"] = origin
        h["Access-Control-Allow-Methods"] = "GET, POST"
        h["Access-Control-Allow-Headers"] = "Content-Type, X-CSRF-Token"
        h["Vary"] = "Origin"
    return resp
