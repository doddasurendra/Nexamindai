"""Knowledge base ingestion, retrieval and grounded-answer behaviour."""
from __future__ import annotations


def test_knowledge_base_upload_and_retrieval(client, auth):
    kb = client.post("/api/knowledge-bases", json={"name": "Docs", "description": "test"}, headers=auth)
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    content = b"NexaMind supports retrieval augmented generation. The vector store is local by default."
    upload = client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        files={"file": ("notes.txt", content, "text/plain")},
        headers=auth,
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["status"] == "ready"

    query = client.post(
        "/api/rag/query",
        json={"knowledge_base_id": kb_id, "query": "What does NexaMind support?", "top_k": 3},
        headers=auth,
    )
    assert query.status_code == 200, query.text
    hits = query.json()["hits"]
    assert hits
    assert "retrieval augmented generation" in hits[0]["content"].lower()


def test_rag_answer_without_provider_is_honest(client, auth):
    kb_id = client.post("/api/knowledge-bases", json={"name": "Empty"}, headers=auth).json()["id"]
    response = client.post(
        "/api/rag/answer",
        json={"knowledge_base_id": kb_id, "query": "Anything?"},
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] is None or body["answer"].startswith("I could not find")
    assert "notice" in body or body["hits"] == []


def test_document_extract_endpoint(client, auth):
    response = client.post(
        "/api/documents/extract",
        files={"file": ("sample.csv", b"a,b\n1,2\n", "text/csv")},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert "a | b" in response.json()["text"]
