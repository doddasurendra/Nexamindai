"""Workflow engine and approval gate tests."""
from __future__ import annotations


def _workflow(client, auth, graph, name="Flow"):
    response = client.post("/api/workflows", json={"name": name, "description": "", "graph": graph}, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()


def test_linear_workflow_runs_and_logs(client, auth):
    workflow = _workflow(
        client,
        auth,
        {
            "nodes": [
                {"id": "start", "type": "trigger", "config": {}},
                {"id": "t", "type": "transform", "config": {"template": "Hello {input}"}},
                {"id": "n", "type": "notify", "config": {"message": "done"}},
            ],
            "edges": [{"from": "start", "to": "t"}, {"from": "t", "to": "n"}],
        },
    )
    run = client.post(f"/api/workflows/{workflow['id']}/run", json={"input": {"name": "Nexa"}}, headers=auth)
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "completed"
    assert len(body["logs"]) == 3
    assert body["logs"][0]["status"] == "ok"


def test_approval_gate_blocks_until_approved(client, auth):
    workflow = _workflow(
        client,
        auth,
        {
            "nodes": [
                {"id": "start", "type": "trigger", "config": {}},
                {"id": "gate", "type": "approval", "config": {"message": "Approve send"}},
                {"id": "n", "type": "notify", "config": {"message": "sent"}},
            ],
            "edges": [{"from": "start", "to": "gate"}, {"from": "gate", "to": "n"}],
        },
        name="Approval flow",
    )
    run = client.post(f"/api/workflows/{workflow['id']}/run", json={"input": {}}, headers=auth).json()
    assert run["status"] == "awaiting_approval"
    assert run["approval_token"]

    approved = client.post(
        f"/api/workflows/executions/{run['id']}/approve",
        json={"token": run["approval_token"], "approved": True},
        headers=auth,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "completed"


def test_unapproved_token_is_rejected(client, auth):
    workflow = _workflow(
        client,
        auth,
        {
            "nodes": [
                {"id": "start", "type": "trigger", "config": {}},
                {"id": "gate", "type": "approval", "config": {}},
            ],
            "edges": [{"from": "start", "to": "gate"}],
        },
        name="Gate",
    )
    run = client.post(f"/api/workflows/{workflow['id']}/run", json={"input": {}}, headers=auth).json()
    response = client.post(
        f"/api/workflows/executions/{run['id']}/approve",
        json={"token": "wrong", "approved": True},
        headers=auth,
    )
    assert response.status_code == 409
