"""Functional tests for the web interface (Flask test client)."""
import re

import pytest

from tests.helpers import make_engine
from web import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(engine=make_engine(), config={"DATABASE_PATH": str(tmp_path / "t.db"), "TESTING": False})


@pytest.fixture
def client(app):
    return app.test_client()


def token(client) -> str:
    html = client.get("/").get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def test_index_has_core_ui(client):
    html = client.get("/").get_data(as_text=True)
    for needle in ("search-input", "theme-toggle", "skip-link", "menu-toggle", "cookie-banner", "to-top",
                   "contact-fab", "<details>", "Last updated", 'id="genre"', "panel-top", "progress"):
        assert needle in html, needle


def test_no_inline_scripts_or_styles(client):
    html = client.get("/").get_data(as_text=True)
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)
    assert " style=" not in html and "onclick=" not in html


def test_health_and_meta(client):
    assert client.get("/healthz").get_json()["status"] == "ok"
    meta = client.get("/api/meta").get_json()
    assert "Sci-Fi" in meta["genres"] and meta["last_updated"]


def test_search_suggestions(client):
    assert any("Toy Story" in s for s in client.get("/api/search?q=toy").get_json()["suggestions"])
    assert client.get("/api/search?q=").get_json()["suggestions"] == []


def test_recommend_returns_similarity_scores(client):
    data = client.get("/api/recommend?title=Alien&n=3&min_ratings=1").get_json()
    assert len(data["results"]) == 3 and all(0 <= r["score"] <= 1 for r in data["results"])
    assert data["query"].startswith("Alien")


def test_genre_filter_and_top_rated(client):
    rows = client.get("/api/top?genre=Animation&min_ratings=1&n=5").get_json()["results"]
    assert rows and all("Animation" in r["genres"] for r in rows)


def test_profile_recommendations(client):
    t = token(client)
    r = client.post("/api/profile?min_ratings=1&n=3", json={"ratings": {"Toy Story": 5, "Up": 5}},
                    headers={"X-CSRF-Token": t})
    assert r.status_code == 200 and len(r.get_json()["results"]) == 3


def test_unknown_movie_is_404_with_friendly_message(client):
    r = client.get("/api/recommend?title=zzzzqqqq")
    assert r.status_code == 404 and "No movie found" in r.get_json()["error"]


def test_404_page_is_generic(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "Traceback" not in r.get_data(as_text=True)
