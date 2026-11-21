"""Security checklist tests: behave like an untrusted user and try to break things."""
import os
import re

import pytest
from werkzeug.security import generate_password_hash

from tests.helpers import make_engine
from web import create_app
from web import db

GOOD = {
    "name": "Asha",
    "email": "asha@example.com",
    "message": "Great project, thank you!"
}


@pytest.fixture
def app(tmp_path):
    return create_app(engine=make_engine(), config={
        "DATABASE_PATH": str(tmp_path / "t.db"),
        "ADMIN_PASSWORD_HASH": generate_password_hash("correct horse"),
        "ALLOWED_ORIGINS": {"https://friend.example"}
    })


@pytest.fixture
def client(app):
    return app.test_client()


def token(client) -> str:
    return re.search(
        r'name="csrf-token" content="([^"]+)"',
        client.get("/").get_data(as_text=True)
    ).group(1)


def post_feedback(client, body=None, tok=None):
    return client.post(
        "/api/feedback",
        json=body if body is not None else GOOD,
        headers={"X-CSRF-Token": tok or token(client)}
    )


# ---- 11/12: errors and debug --------------------------------------------------

def test_unexpected_errors_do_not_leak_details(app):
    app.add_url_rule("/api/boom", "boom", lambda: 1 / 0)
    r = app.test_client().get("/api/boom")
    body = r.get_data(as_text=True)

    assert r.status_code == 500
    assert "ZeroDivision" not in body
    assert "Traceback" not in body
    assert not app.debug


def test_production_requires_secret_key():
    old = {k: os.environ.pop(k, None) for k in ("SECRET_KEY",)}
    os.environ["APP_ENV"] = "production"

    try:
        with pytest.raises(RuntimeError):
            create_app(engine=make_engine())
    finally:
        os.environ.pop("APP_ENV")

        for k, v in old.items():
            if v is not None:
                os.environ[k] = v


# ---- 19: headers, CORS, cookies -----------------------------------------------

def test_security_headers_present(client):
    h = client.get("/").headers

    assert "default-src 'self'" in h["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in h
    assert "Permissions-Policy" in h


def test_cors_off_by_default_and_exact_whitelist(client):
    assert "Access-Control-Allow-Origin" not in client.get(
        "/api/meta",
        headers={"Origin": "https://evil.example"}
    ).headers

    ok = client.get(
        "/api/meta",
        headers={"Origin": "https://friend.example"}
    ).headers

    assert ok["Access-Control-Allow-Origin"] == "https://friend.example"


def test_session_cookie_flags(client):
    cookie = client.get("/").headers.get("Set-Cookie", "")

    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_api_responses_not_cached(client):
    assert client.get("/api/meta").headers["Cache-Control"] == "no-store"


# ---- CSRF / origin ------------------------------------------------------------

def test_post_without_csrf_token_rejected(client):
    assert client.post("/api/feedback", json=GOOD).status_code == 403


def test_post_with_wrong_token_rejected(client):
    token(client)

    assert client.post(
        "/api/feedback",
        json=GOOD,
        headers={"X-CSRF-Token": "wrong"}
    ).status_code == 403


def test_cross_site_origin_blocked_even_with_token(client):
    r = client.post(
        "/api/feedback",
        json=GOOD,
        headers={
            "X-CSRF-Token": token(client),
            "Origin": "https://evil.example"
        }
    )

    assert r.status_code == 403


# ---- 13/14/16: validation, sanitising, injection -------------------------------

@pytest.mark.parametrize(
    "query",
    ["n=0", "n=999", "n=abc", "min_ratings=-5", "genre=Nope"]
)
def test_bad_query_params_rejected(client, query):
    assert client.get(f"/api/top?{query}").status_code == 400


def test_overlong_title_rejected(client):
    assert client.get(
        "/api/recommend?title=" + "a" * 500
    ).status_code == 400


def test_profile_validation(client):
    h = {"X-CSRF-Token": token(client)}

    assert client.post(
        "/api/profile",
        json={"ratings": {"Up": 99}},
        headers=h
    ).status_code == 400

    assert client.post(
        "/api/profile",
        json={"ratings": {}},
        headers=h
    ).status_code == 400

    assert client.post(
        "/api/profile",
        json=["x"],
        headers=h
    ).status_code == 400

    many = {f"movie {i}": 4 for i in range(31)}

    assert client.post(
        "/api/profile",
        json={"ratings": many},
        headers=h
    ).status_code == 400


def test_feedback_validation(client):
    tok = token(client)

    assert post_feedback(
        client,
        {**GOOD, "email": "not-an-email"},
        tok
    ).status_code == 400

    assert post_feedback(
        client,
        {**GOOD, "message": "short"},
        tok
    ).status_code == 400

    assert post_feedback(
        client,
        {**GOOD, "name": ""},
        tok
    ).status_code == 400

    assert post_feedback(
        client,
        {**GOOD, "message": "x" * 1001},
        tok
    ).status_code == 400


def test_oversized_body_rejected(client):
    tok = token(client)

    r = client.post(
        "/api/feedback",
        data=b"x" * 70000,
        content_type="application/json",
        headers={"X-CSRF-Token": tok}
    )

    assert r.status_code == 413


def test_sql_injection_is_stored_as_plain_text(app, client):
    evil = "'); DROP TABLE feedback;-- long enough message"

    assert post_feedback(
        client,
        {**GOOD, "message": evil}
    ).status_code == 201

    rows = db.list_feedback(app.config["DATABASE_PATH"])

    assert len(rows) == 1
    assert rows[0]["message"] == evil


def test_honeypot_discards_bots(app, client):
    assert post_feedback(
        client,
        {**GOOD, "website": "http://spam"}
    ).status_code == 201

    assert db.list_feedback(app.config["DATABASE_PATH"]) == []


def test_invalid_utm_values_ignored(app, client):
    post_feedback(
        client,
        {
            **GOOD,
            "utm_source": "good-source",
            "utm_medium": "<script>"
        }
    )

    row = db.list_feedback(app.config["DATABASE_PATH"])[0]

    assert row["utm_source"] == "good-source"
    assert row["utm_medium"] is None


# ---- 17: rate limiting ---------------------------------------------------------

def test_feedback_rate_limited(client):
    tok = token(client)

    codes = [
        post_feedback(client, tok=tok).status_code
        for _ in range(7)
    ]

    assert codes[:5] == [201] * 5
    assert codes[5] == 429


def test_login_rate_limited(client):
    codes = []

    for _ in range(7):
        tok = token(client)

        codes.append(
            client.post(
                "/admin/login",
                data={
                    "password": "wrong",
                    "csrf_token": tok
                }
            ).status_code
        )

    assert 429 in codes
    assert codes[0] == 401


# ---- 4/5/6/10: authentication and permissions ---------------------------------

def test_admin_hidden_when_not_configured(tmp_path):
    app = create_app(
        engine=make_engine(),
        config={
            "DATABASE_PATH": str(tmp_path / "x.db"),
            "ADMIN_PASSWORD_HASH": ""
        }
    )

    c = app.test_client()

    assert c.get("/admin").status_code == 404
    assert c.get("/admin/login").status_code == 404


def test_admin_requires_login(client):
    r = client.get("/admin")

    assert r.status_code == 302
    assert "/admin/login" in r.headers["Location"]


def test_wrong_password_rejected_generic_message(client):
    r = client.post(
        "/admin/login",
        data={
            "password": "nope",
            "csrf_token": token(client)
        }
    )

    assert r.status_code == 401
    assert "Invalid credentials" in r.get_data(as_text=True)


def test_login_without_csrf_rejected(client):
    assert client.post(
        "/admin/login",
        data={"password": "correct horse"}
    ).status_code == 403


def login(client):
    r = client.post(
        "/admin/login",
        data={
            "password": "correct horse",
            "csrf_token": token(client)
        }
    )

    assert r.status_code == 302


def test_admin_session_flow_and_delete_requires_csrf(app, client):
    post_feedback(client)
    login(client)

    assert client.get("/admin").status_code == 200

    fid = db.list_feedback(app.config["DATABASE_PATH"])[0]["id"]

    assert client.post(
        f"/admin/delete/{fid}"
    ).status_code == 403

    assert len(db.list_feedback(app.config["DATABASE_PATH"])) == 1

    tok = re.search(
        r'name="csrf_token" value="([^"]+)"',
        client.get("/admin").get_data(as_text=True)
    ).group(1)

    assert client.post(
        f"/admin/delete/{fid}",
        data={"csrf_token": tok}
    ).status_code == 302

    assert db.list_feedback(app.config["DATABASE_PATH"]) == []


def test_unauthenticated_user_cannot_delete(app, client):
    post_feedback(client)

    fid = db.list_feedback(app.config["DATABASE_PATH"])[0]["id"]

    r = client.post(
        f"/admin/delete/{fid}",
        data={"csrf_token": token(client)}
    )

    assert r.status_code == 302
    assert len(db.list_feedback(app.config["DATABASE_PATH"])) == 1


def test_admin_cannot_be_reached_after_logout(client):
    login(client)

    tok = re.search(
        r'name="csrf_token" value="([^"]+)"',
        client.get("/admin").get_data(as_text=True)
    ).group(1)

    client.post(
        "/admin/logout",
        data={"csrf_token": tok}
    )

    assert client.get("/admin").status_code == 302


# ---- 14: XSS -------------------------------------------------------------------

def test_stored_xss_is_escaped_in_admin_view(client):
    post_feedback(
        client,
        {
            **GOOD,
            "name": "<script>alert(1)</script>",
            "message": "<img src=x onerror=alert(1)> hello"
        }
    )

    login(client)

    html = client.get("/admin").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html


# ---- 7/8: data isolation + database file ---------------------------------------

def test_database_file_not_world_readable(app):
    # Windows does not enforce Unix permission bits through chmod.
    # Keep this security assertion active on Linux and macOS.
    if os.name == "nt":
        pytest.skip("Unix file permission bits are not enforced on Windows")

    mode = os.stat(app.config["DATABASE_PATH"]).st_mode & 0o777

    assert mode & 0o077 == 0


def test_taste_profile_never_stored_on_server(app, client):
    h = {"X-CSRF-Token": token(client)}

    client.post(
        "/api/profile?min_ratings=1",
        json={"ratings": {"Toy Story": 5}},
        headers=h
    )

    assert db.list_feedback(app.config["DATABASE_PATH"]) == []