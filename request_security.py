"""Shared controls for Flask forms, request diagnostics, and rate limits."""
import json
import logging
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from math import ceil
from secrets import compare_digest, token_urlsafe
from threading import Lock
from time import monotonic
from uuid import uuid4

from flask import abort, current_app, g, request, session
from werkzeug.exceptions import HTTPException, TooManyRequests


logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
logger.propagate = False


def configure_request_security(app):
    app.config.update(
        SESSION_COOKIE_SECURE=app.config["ON_RENDER"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=32 * 1024,
        MAX_FORM_PARTS=32,
    )
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(check_request)
    app.after_request(finish_request)
    app.register_error_handler(HTTPException, http_error)
    app.register_error_handler(Exception, unexpected_error)


def log_event(event, outcome, *, level=logging.INFO, status=None):
    logger.log(level, json.dumps({
        "time": datetime.now(timezone.utc).isoformat(),
        "severity": logging.getLevelName(level),
        "request_id": str(g.request_id),
        "endpoint": request.endpoint,
        "event": event,
        "outcome": outcome,
        "status": status,
    }))


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = token_urlsafe(32)
    return session["csrf_token"]


def check_request():
    g.request_id = uuid4()
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if (request.content_length or 0) > current_app.config["MAX_CONTENT_LENGTH"]:
        abort(413)

    expected = session.get("csrf_token")
    submitted = request.form.get("csrf_token", "")
    if not isinstance(expected, str) or not expected or not compare_digest(
        expected.encode("utf-8"), submitted.encode("utf-8")
    ):
        log_event("csrf", "rejected", status=400)
        abort(400)


def finish_request(response):
    response.headers["X-Request-ID"] = str(g.request_id)
    response.headers["X-Content-Type-Options"] = "nosniff"
    log_event("request", "error" if response.status_code >= 400 else "completed",
              status=response.status_code)
    return response


def http_error(error):
    response = error.get_response()
    response.set_data({
        400: "Invalid request. Reload the page and try again.",
        403: "Access denied.",
        404: "Page not found.",
        405: "Method not allowed.",
        413: "Request is too large.",
        429: "Too many requests. Try again later.",
    }.get(error.code, "The request could not be completed."))
    response.mimetype = "text/plain"
    return response


def unexpected_error(_error):
    log_event("application", "error", level=logging.ERROR, status=500)
    return "The request could not be completed.", 500


class RateLimit:
    def __init__(self, attempts, seconds):
        self.attempts = attempts
        self.seconds = seconds
        self.windows = {}
        self.lock = Lock()

    def check(self, key):
        with self.lock:
            now = monotonic()
            while self.windows:
                oldest = next(iter(self.windows))
                if self.windows[oldest][1] > now:
                    break
                del self.windows[oldest]

            window = self.windows.get(key)
            if window:
                count, expires = window
                if count >= self.attempts:
                    return ceil(expires - now)
                self.windows[key] = (count + 1, expires)
            elif len(self.windows) < 4096:
                self.windows[key] = (1, now + self.seconds)
            else:
                _, expires = next(iter(self.windows.values()))
                return ceil(expires - now)
            return None


login_limit = RateLimit(attempts=10, seconds=15 * 60)
advisor_limit = RateLimit(attempts=5, seconds=60)


def enforce_limit(limit, key, event):
    retry_after = limit.check(key)
    if retry_after is not None:
        log_event(event, "rate_limited", status=429)
        raise TooManyRequests(retry_after=retry_after)


def check_login_limit():
    client = request.remote_addr or "unknown"
    if current_app.config["ON_RENDER"]:
        # Render's public Cloudflare edge sets this header, replacing a caller's value.
        ip = request.headers.get("CF-Connecting-IP")
        if ip:
            try:
                client = str(ip_address(ip))
            except ValueError:
                pass
    enforce_limit(login_limit, client, "login")


def check_advisor_limit(user_id):
    """Call after the advisor route has authenticated the user."""
    enforce_limit(advisor_limit, user_id, "advisor")
