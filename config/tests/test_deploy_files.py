"""
The deploy files are code too. These checks catch the mistakes that hurt most once the
app is on the internet: a secret copied into the image, or an unsafe setting.
"""

import importlib
import runpy
import sys
from pathlib import Path

import pytest
from django.conf import settings

ROOT = Path(settings.BASE_DIR)


def lines(name: str) -> list[str]:
    return [line.strip() for line in (ROOT / name).read_text(encoding="utf-8").splitlines()]


def test_secrets_never_go_into_the_image_or_the_repository():
    for name in (".dockerignore", ".gitignore"):
        assert ".env" in lines(name), f"{name} must exclude .env"
    assert "COPY .env" not in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_image_runs_as_a_normal_user_and_migrates_before_serving():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "\nUSER " in dockerfile
    assert "migrate --noinput && exec gunicorn" in dockerfile
    assert "0.0.0.0:${PORT}" in dockerfile  # hosts such as Render choose the port


def test_production_server_is_installed():
    assert any(line.startswith("gunicorn==") for line in lines("requirements.txt"))


@pytest.fixture
def production_env(monkeypatch):
    """Made-up production values, whatever your own .env says; put everything back after."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@db.example:5432/app")
    monkeypatch.setenv("USE_SQLITE", "False")
    base = importlib.import_module("config.settings.base")
    importlib.reload(base)  # base.py reads the environment when it runs, so run it again
    sys.modules.pop("config.settings.production", None)
    yield
    monkeypatch.undo()
    importlib.reload(base)
    sys.modules.pop("config.settings.production", None)


def test_production_settings_stay_strict(production_env):
    production = runpy.run_module("config.settings.production")
    assert production["DEBUG"] is False
    assert production["SECURE_SSL_REDIRECT"] and production["SESSION_COOKIE_SECURE"]
    assert production["DATABASES"]["default"]["OPTIONS"]["sslmode"] == "require"


def test_local_docker_settings_only_relax_https_and_database_ssl(production_env):
    local = runpy.run_module("config.settings.docker_local")
    assert local["DEBUG"] is False  # still production in every other way
    assert local["SECURE_SSL_REDIRECT"] is False and local["SESSION_COOKIE_SECURE"] is False
    assert "sslmode" not in local["DATABASES"]["default"]["OPTIONS"]
