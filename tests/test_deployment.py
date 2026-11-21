"""Checks that matter for serverless deployment (Vercel)."""
import re
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from tests.helpers import make_engine
from web import create_app

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def app(tmp_path):
    return create_app(engine=make_engine(), config={
        "FEEDBACK_ENABLED": False, "DATABASE_PATH": str(tmp_path / "never_created.db"),
        "ADMIN_PASSWORD_HASH": generate_password_hash("correct horse")})


def test_runtime_has_no_heavy_dependencies():
    for folder in ("src", "web"):
        for path in (ROOT / folder).rglob("*.py"):
            text = path.read_text()
            assert not re.search(r"^\s*(import|from)\s+(sklearn|scipy|matplotlib)", text, re.M), path


def test_runtime_requirements_are_lean():
    reqs = (ROOT / "requirements.txt").read_text().lower()
    for heavy in ("scikit-learn", "scipy", "matplotlib", "streamlit", "pytest"):
        assert heavy not in reqs


def test_vercel_files_present():
    assert (ROOT / "vercel.json").exists() and (ROOT / "api" / "index.py").exists()
    assert "from server import app" in (ROOT / "api" / "index.py").read_text()


def test_feedback_disabled_hides_contact_ui(app):
    html = app.test_client().get("/").get_data(as_text=True)
    assert "contact-fab" not in html and "contact-dialog" not in html and "nav-contact" not in html


def test_feedback_disabled_returns_503_and_creates_no_database(app, tmp_path):
    c = app.test_client()
    tok = re.search(r'name="csrf-token" content="([^"]+)"', c.get("/").get_data(as_text=True)).group(1)
    r = c.post("/api/feedback", json={"name": "A", "email": "a@b.co", "message": "hello there friend"},
               headers={"X-CSRF-Token": tok})
    assert r.status_code == 503 and not (tmp_path / "never_created.db").exists()


def test_admin_hidden_when_feedback_disabled(app):
    assert app.test_client().get("/admin/login").status_code == 404


def test_recommendations_still_work_when_feedback_disabled(app):
    data = app.test_client().get("/api/recommend?title=Alien&n=3&min_ratings=1").get_json()
    assert len(data["results"]) == 3
