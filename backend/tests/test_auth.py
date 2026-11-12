"""Authentication, authorization and input validation tests."""
from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_and_me(client):
    email = "alice@example.com"
    registration = client.post("/api/auth/register", json={"email": email, "password": "strong-pass-1", "name": "Alice"})
    assert registration.status_code == 201, registration.text
    token = registration.json()["access_token"]

    duplicate = client.post("/api/auth/register", json={"email": email, "password": "strong-pass-2"})
    assert duplicate.status_code == 409

    login = client.post("/api/auth/login", json={"email": email, "password": "strong-pass-1"})
    assert login.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_rejects_bad_email_and_weak_password(client):
    assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "12345678"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "bob@example.com", "password": "short"}).status_code == 422


def test_protected_routes_require_token(client):
    assert client.get("/api/conversations").status_code == 401
    assert client.get("/api/agents").status_code == 401


def test_wrong_password_is_rejected(client):
    client.post("/api/auth/register", json={"email": "carol@example.com", "password": "right-password-1"})
    response = client.post("/api/auth/login", json={"email": "carol@example.com", "password": "wrong-password"})
    assert response.status_code == 401
