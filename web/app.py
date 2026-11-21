"""Flask application factory."""
from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

from src import MovieNotFoundError, MovieRecommender

from . import db
from .security import (EMAIL_RE, UTM_RE, RateLimiter, ValidationError, apply_security_headers, clean_text,
                       csrf_token, csrf_valid, int_param, origin_allowed, rating_param)

LAST_UPDATED = os.environ.get("APP_LAST_UPDATED", "2026-11-19")
MAX_PROFILE_ITEMS = 30


def _df_to_json(df) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def create_app(engine: MovieRecommender | None = None, config: dict | None = None) -> Flask:
    try:  # optional: read a local .env file (never committed, see .env.example)
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    app = Flask(__name__)
    production = os.environ.get("APP_ENV", "development") == "production"
    on_vercel = bool(os.environ.get("VERCEL"))  # serverless: read-only disk, so no local database
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        if production:
            raise RuntimeError("SECRET_KEY must be set in production (see .env.example).")
        secret = secrets.token_hex(32)  # dev only: sessions reset on every restart
    app.config.update(
        SECRET_KEY=secret,
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        DATABASE_PATH=os.environ.get("DATABASE_PATH", str(Path("instance") / "feedback.db")),
        FEEDBACK_ENABLED=os.environ.get("FEEDBACK_ENABLED", "0" if on_vercel else "1") == "1",
        ADMIN_PASSWORD_HASH=os.environ.get("ADMIN_PASSWORD_HASH", ""),
        ALLOWED_ORIGINS={o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()},
        PRODUCTION=production,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    proxies = int(os.environ.get("TRUSTED_PROXY_COUNT", "1" if on_vercel else "0"))
    if proxies:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    engine = engine or MovieRecommender()
    limiter = RateLimiter()
    app.extensions["limiter"] = limiter
    if app.config["FEEDBACK_ENABLED"]:
        db.init_db(app.config["DATABASE_PATH"])
    log = logging.getLogger("movie-recommender")

    # ------------------------------------------------------------ hooks
    @app.before_request
    def guard_post():
        if request.method == "POST":
            if not origin_allowed(app.config["ALLOWED_ORIGINS"]):
                return jsonify(error="Cross-site request blocked."), 403
            if not csrf_valid():
                return jsonify(error="Security token missing or expired. Please reload the page."), 403

    @app.after_request
    def headers(resp):
        return apply_security_headers(resp, app.config["PRODUCTION"], app.config["ALLOWED_ORIGINS"])

    # --------------------------------------------------- error handling
    def _error(code: int, message: str):
        if request.path.startswith("/api") or request.is_json:
            return jsonify(error=message), code
        return render_template("error.html", code=code, message=message), code

    @app.errorhandler(ValidationError)
    def _validation(e):
        return _error(400, str(e))

    @app.errorhandler(MovieNotFoundError)
    def _not_found_movie(e):
        return _error(404, str(e))

    for code, msg in {404: "Page not found.", 405: "Method not allowed.", 413: "Request too large.",
                      429: "Too many requests."}.items():
        app.register_error_handler(code, lambda e, c=code, m=msg: _error(c, m))

    @app.errorhandler(Exception)
    def _unexpected(e):
        if hasattr(e, "code") and isinstance(e.code, int) and e.code < 500:
            return _error(e.code, "Request could not be completed.")
        log.exception("Unhandled error")  # details go to the server log only
        return _error(500, "Something went wrong on our side. Please try again later.")

    # ------------------------------------------------------- public pages
    @app.get("/")
    def index():
        return render_template("index.html", csrf=csrf_token(), last_updated=LAST_UPDATED,
                               feedback_enabled=app.config["FEEDBACK_ENABLED"],
                               dataset=engine.dataset, n_movies=len(engine.movies),
                               n_ratings=len(engine.ratings))

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    # ------------------------------------------------------------ JSON API
    def _filters(default_min: int):
        return dict(
            n=int_param(request.args.get("n"), "n", 10, 1, 30),
            min_ratings=int_param(request.args.get("min_ratings"), "min_ratings", default_min, 1, 2000),
            genre=_genre(request.args.get("genre")),
        )

    def _genre(raw):
        if not raw or raw == "Any":
            return None
        raw = clean_text(raw, "genre", 1, 40)
        if raw not in engine.all_genres:
            raise ValidationError("Unknown genre.")
        return raw

    @app.get("/api/meta")
    @limiter.limit("api", 120, 60)
    def meta():
        return jsonify(genres=engine.all_genres, dataset=engine.dataset, movies=len(engine.movies),
                       ratings=len(engine.ratings), last_updated=LAST_UPDATED)

    @app.get("/api/search")
    @limiter.limit("api", 120, 60)
    def search():
        q = clean_text(request.args.get("q", ""), "q", 0, 80)
        return jsonify(suggestions=engine.search(q, 8) if q else [])

    @app.get("/api/recommend")
    @limiter.limit("api", 120, 60)
    def recommend():
        title = clean_text(request.args.get("title", ""), "title", 1, 120)
        f = _filters(20)
        df = engine.recommend(title, f["n"], f["genre"], f["min_ratings"])
        return jsonify(query=engine.resolve_title(title), results=_df_to_json(df))

    @app.get("/api/top")
    @limiter.limit("api", 120, 60)
    def top():
        f = _filters(50)
        return jsonify(results=_df_to_json(engine.top_rated(f["n"], f["genre"], f["min_ratings"])))

    @app.post("/api/profile")
    @limiter.limit("profile", 60, 60)
    def profile():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("ratings"), dict):
            raise ValidationError("Send a JSON object with a 'ratings' mapping.")
        raw = body["ratings"]
        if not 1 <= len(raw) <= MAX_PROFILE_ITEMS:
            raise ValidationError(f"Rate between 1 and {MAX_PROFILE_ITEMS} movies.")
        ratings = {clean_text(t, "title", 1, 120): rating_param(r, str(t)) for t, r in raw.items()}
        f = _filters(20)
        df = engine.recommend_for_ratings(ratings, f["n"], f["genre"], f["min_ratings"])
        return jsonify(results=_df_to_json(df))

    @app.post("/api/feedback")
    @limiter.limit("feedback", 5, 3600)
    def feedback():
        if not app.config["FEEDBACK_ENABLED"]:
            return jsonify(error="Feedback is not available on this deployment."), 503
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValidationError("Invalid form data.")
        if body.get("website"):  # honeypot: real users never fill this hidden field
            return jsonify(ok=True), 201
        name = clean_text(body.get("name"), "Name", 1, 80)
        email = clean_text(body.get("email"), "Email", 3, 120)
        if not EMAIL_RE.match(email):
            raise ValidationError("Please enter a valid email address.")
        message = clean_text(body.get("message"), "Message", 10, 1000)
        utm = {}
        for key in ("utm_source", "utm_medium", "utm_campaign"):
            val = body.get(key)
            if isinstance(val, str) and UTM_RE.match(val):
                utm[key] = val
        db.add_feedback(app.config["DATABASE_PATH"], name, email, message, utm)
        return jsonify(ok=True), 201

    # ------------------------------------------------------------- admin
    def admin_enabled() -> bool:
        return bool(app.config["ADMIN_PASSWORD_HASH"]) and app.config["FEEDBACK_ENABLED"]

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not admin_enabled():
                return _error(404, "Page not found.")
            if not session.get("admin"):  # permission is checked on the server for every request
                return redirect(url_for("admin_login"))
            return fn(*a, **kw)
        return wrapper

    @app.route("/admin/login", methods=["GET", "POST"])
    @limiter.limit("login", 5, 600)
    def admin_login():
        if not admin_enabled():
            return _error(404, "Page not found.")
        error = None
        if request.method == "POST":
            password = request.form.get("password", "")[:200]
            if check_password_hash(app.config["ADMIN_PASSWORD_HASH"], password):
                session.clear()
                session["admin"] = True
                session["csrf"] = secrets.token_urlsafe(32)
                session.permanent = True
                return redirect(url_for("admin_dashboard"))
            error = "Invalid credentials."
            return render_template("admin_login.html", csrf=csrf_token(), error=error), 401
        return render_template("admin_login.html", csrf=csrf_token(), error=error)

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        rows = db.list_feedback(app.config["DATABASE_PATH"])
        return render_template("admin.html", rows=rows, csrf=csrf_token())

    @app.post("/admin/delete/<int:fid>")
    @admin_required
    def admin_delete(fid: int):
        db.delete_feedback(app.config["DATABASE_PATH"], fid)
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("index"))

    return app
