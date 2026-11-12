"""Test fixtures: isolated SQLite database, signed-in client."""
from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path("./data/test_nexamind.db")
if TEST_DB.exists():
    TEST_DB.unlink()

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_nexamind.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "password": "super-secret-1", "name": "Tester"},
    )
    if response.status_code == 409:
        response = client.post(
            "/api/auth/login", json={"email": "tester@example.com", "password": "super-secret-1"}
        )
    assert response.status_code in (200, 201), response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def conversation(client, auth):
    response = client.post("/api/conversations", json={"title": "Test chat"}, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()
