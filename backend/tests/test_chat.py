"""Chat persistence and streaming tests with a mocked provider (no fake successes at runtime)."""
from __future__ import annotations

import json


async def fake_chat(messages, model=None, **kwargs):
    return {
        "text": "Hello from the mocked model.",
        "model": model or "openai/gpt-4o-mini",
        "tokens_in": 12,
        "tokens_out": 6,
        "cost": 0.0001,
        "latency_ms": 5,
        "raw": {},
    }


async def fake_stream(messages, model=None, **kwargs):
    yield {"type": "delta", "text": "Hello "}
    yield {"type": "delta", "text": "stream."}
    yield {"type": "done", "model": model or "openai/gpt-4o-mini", "tokens_in": 10, "tokens_out": 4, "cost": 0.0001, "latency_ms": 3}


def test_conversation_crud(client, auth):
    created = client.post("/api/conversations", json={"title": "First"}, headers=auth)
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    renamed = client.patch(f"/api/conversations/{conversation_id}", json={"title": "Renamed"}, headers=auth)
    assert renamed.json()["title"] == "Renamed"

    listing = client.get("/api/conversations?q=Renamed", headers=auth)
    assert any(item["id"] == conversation_id for item in listing.json())

    deleted = client.delete(f"/api/conversations/{conversation_id}", headers=auth)
    assert deleted.status_code == 204
    assert client.get(f"/api/conversations/{conversation_id}", headers=auth).status_code == 404


def test_chat_complete_persists_messages(client, auth, conversation, monkeypatch):
    from app.services import openrouter

    monkeypatch.setattr(openrouter, "chat", fake_chat)
    response = client.post(
        "/api/chat/complete",
        json={"conversation_id": conversation["id"], "content": "Hi"},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert response.json()["content"] == "Hello from the mocked model."

    detail = client.get(f"/api/conversations/{conversation['id']}", headers=auth).json()
    roles = [message["role"] for message in detail["messages"]]
    assert roles == ["user", "assistant"]


def test_chat_stream_sse(client, auth, conversation, monkeypatch):
    from app.services import openrouter

    monkeypatch.setattr(openrouter, "chat_stream", fake_stream)
    response = client.post(
        "/api/chat/stream",
        json={"conversation_id": conversation["id"], "content": "Stream please"},
        headers=auth,
    )
    assert response.status_code == 200
    events = [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert any(event["type"] == "delta" for event in events)
    assert any(event["type"] == "done" for event in events)

    detail = client.get(f"/api/conversations/{conversation['id']}", headers=auth).json()
    assert any(m["content"] == "Hello stream." for m in detail["messages"])


def test_export_conversation(client, auth, conversation, monkeypatch):
    from app.services import openrouter

    monkeypatch.setattr(openrouter, "chat", fake_chat)
    client.post("/api/chat/complete", json={"conversation_id": conversation["id"], "content": "Export me"}, headers=auth)
    markdown = client.get(f"/api/conversations/{conversation['id']}/export?format=markdown", headers=auth)
    assert markdown.status_code == 200
    assert "Export me" in markdown.text
    payload = client.get(f"/api/conversations/{conversation['id']}/export?format=json", headers=auth)
    assert payload.json()["messages"]


def test_chat_requires_openrouter_when_unconfigured(client, auth):
    conversation = client.post("/api/conversations", json={"title": "No key"}, headers=auth).json()
    response = client.post(
        "/api/chat/complete", json={"conversation_id": conversation["id"], "content": "Hi"}, headers=auth
    )
    assert response.status_code == 503
    assert response.json()["code"] == "integration_not_configured"
