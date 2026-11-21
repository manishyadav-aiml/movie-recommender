"""Tests for serverless deployment compatibility (Vercel)."""

import ast
import re
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from tests.helpers import make_engine
from web import create_app


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def app(tmp_path):
    """Create an isolated Flask application for deployment tests."""
    return create_app(
        engine=make_engine(),
        config={
            "FEEDBACK_ENABLED": False,
            "DATABASE_PATH": str(tmp_path / "never_created.db"),
            "ADMIN_PASSWORD_HASH": generate_password_hash("correct horse"),
        },
    )


def test_runtime_has_no_heavy_dependencies():
    """Ensure runtime modules do not import unnecessary heavy libraries."""
    forbidden_imports = re.compile(
        r"^\s*(?:import|from)\s+"
        r"(?:sklearn|scipy|matplotlib)(?:\s|\.|$)",
        re.MULTILINE,
    )

    for folder in ("src", "web"):
        folder_path = ROOT / folder

        assert folder_path.exists(), f"Missing runtime folder: {folder}"

        for path in folder_path.rglob("*.py"):
            source = path.read_text(encoding="utf-8")

            assert not forbidden_imports.search(source), (
                f"Heavy dependency imported in runtime module: {path}"
            )


def test_runtime_requirements_are_lean():
    """Ensure development and heavyweight packages are not runtime dependencies."""
    requirements_file = ROOT / "requirements.txt"

    assert requirements_file.exists(), "requirements.txt is missing"

    requirements = requirements_file.read_text(
        encoding="utf-8"
    ).lower()

    forbidden_packages = (
        "scikit-learn",
        "scipy",
        "matplotlib",
        "streamlit",
        "pytest",
    )

    for package in forbidden_packages:
        assert not re.search(
            rf"^\s*{re.escape(package)}(?:\s|[<>=!~;\[]|$)",
            requirements,
            re.MULTILINE,
        ), f"Development dependency found in requirements.txt: {package}"


def test_vercel_flask_entrypoint_present():
    """Verify that server.py exposes the Flask application entry point."""
    server_file = ROOT / "server.py"

    assert server_file.exists(), "server.py is missing"

    source = server_file.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imports_create_app = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "web"
        and any(alias.name == "create_app" for alias in node.names)
        for node in ast.walk(tree)
    )

    assert imports_create_app, (
        "server.py must import create_app from the web package"
    )

    exposes_flask_app = any(
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "app"
            for target in node.targets
        )
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "create_app"
        for node in ast.walk(tree)
    )

    assert exposes_flask_app, (
        "server.py must expose app = create_app()"
    )


def test_feedback_disabled_hides_contact_ui(app):
    """Ensure contact interface elements are hidden when feedback is disabled."""
    response = app.test_client().get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    forbidden_elements = (
        "contact-fab",
        "contact-dialog",
        "nav-contact",
    )

    for element in forbidden_elements:
        assert element not in html, (
            f"Unexpected contact interface element found: {element}"
        )


def test_feedback_disabled_returns_503_and_creates_no_database(app, tmp_path):
    """Ensure feedback endpoints are unavailable without creating a database."""
    client = app.test_client()

    page_response = client.get("/")

    assert page_response.status_code == 200

    html = page_response.get_data(as_text=True)

    csrf_match = re.search(
        r'name="csrf-token"\s+content="([^"]+)"',
        html,
    )

    assert csrf_match is not None, "CSRF token missing from homepage"

    csrf_token = csrf_match.group(1)

    response = client.post(
        "/api/feedback",
        json={
            "name": "A",
            "email": "a@b.co",
            "message": "hello there friend",
        },
        headers={
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 503

    database_file = tmp_path / "never_created.db"

    assert not database_file.exists(), (
        "Feedback-disabled request unexpectedly created a database"
    )


def test_admin_hidden_when_feedback_disabled(app):
    """Ensure the admin login page is unavailable when feedback is disabled."""
    response = app.test_client().get("/admin/login")

    assert response.status_code == 404


def test_recommendations_still_work_when_feedback_disabled(app):
    """Ensure movie recommendations work even when feedback is disabled."""
    response = app.test_client().get(
        "/api/recommend?title=Alien&n=3&min_ratings=1"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert isinstance(data.get("results"), list)
    assert len(data["results"]) == 3