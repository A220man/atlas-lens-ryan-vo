"""End-to-end API integration tests crossing the HTTP boundary."""

from fastapi.testclient import TestClient


def test_chat_import_heal_and_export_workflow(client: TestClient, operator_headers, viewer_headers, admin_headers):
    """Test full conversational DAG workflow: import corrupt chat -> heal -> query -> export -> delete."""
    corrupt_payload = {
        "id": "e2e-chat-01",
        "title": "E2E Broken Tree",
        "history": {
            "messages": {
                "m-root": {"id": "m-root", "parentId": None, "content": "Root question", "role": "user", "timestamp": 10},
                "m-orphan": {"id": "m-orphan", "parentId": "ghost-id", "content": "Orphan node", "role": "assistant", "timestamp": 20},
            },
            "currentId": "m-orphan"
        },
        "messages": []
    }

    # 1. Import with auto-repair
    import_resp = client.post("/api/chats/import?auto_repair=true", json=corrupt_payload, headers=operator_headers)
    assert import_resp.status_code == 200
    import_data = import_resp.json()
    assert import_data["id"] == "e2e-chat-01"
    assert import_data["is_repaired"] is True
    assert import_data["total_messages"] == 2

    # 2. Query chat detail
    get_resp = client.get("/api/chats/e2e-chat-01", headers=viewer_headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["validation_report"]["is_valid"] is True
    assert len(detail["linearized_trajectory"]) == 2

    # 3. Explicit repair trigger
    repair_resp = client.post("/api/chats/e2e-chat-01/repair", headers=operator_headers)
    assert repair_resp.status_code == 200
    assert repair_resp.json()["status"] == "repaired"

    # 4. Export clean chat
    export_resp = client.get("/api/chats/e2e-chat-01/export", headers=viewer_headers)
    assert export_resp.status_code == 200
    exported_data = export_resp.json()
    assert "history" in exported_data

    # 5. Admin deletion
    del_resp = client.delete("/api/chats/e2e-chat-01", headers=admin_headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"


def test_prompt_hygiene_workflow(client: TestClient, viewer_headers, operator_headers):
    """Test prompt hygiene analysis and completion dispatch."""
    payload = {
        "model_id": "test-qwen",
        "reinject_reasoning": False,
        "messages": [
            {"role": "user", "content": "Write hello world in python"},
            {"role": "assistant", "content": "<think>User wants simple python script</think>print('Hello, world!')"}
        ]
    }

    # Inspect endpoint
    inspect_resp = client.post("/api/hygiene/inspect", json=payload, headers=viewer_headers)
    assert inspect_resp.status_code == 200
    data = inspect_resp.json()
    assert data["contains_think_tags"] is True
    assert data["token_savings_pct"] > 0
    assert "<think>" not in data["sanitized_messages"][1]["content"]

    # Completion dispatch with hygiene
    dispatch_payload = {
        "prompt_request": payload,
        "system_instruction": "Test system prompt"
    }
    dispatch_resp = client.post("/api/hygiene/dispatch-completion", json=dispatch_payload, headers=operator_headers)
    assert dispatch_resp.status_code == 200
    disp_data = dispatch_resp.json()
    assert "completion" in disp_data
    assert "hygiene_summary" in disp_data


def test_evaluation_benchmark_workflow(client: TestClient, operator_headers, viewer_headers):
    """Test empirical evaluation benchmark runner and persistence."""
    run_resp = client.post("/api/evaluations/run", json={"sample_count": 10}, headers=operator_headers)
    assert run_resp.status_code == 200
    metrics = run_resp.json()
    assert metrics["sample_count"] == 10
    assert metrics["mean_token_savings_pct"] > 0
    assert metrics["imitation_suppression_pct"] == 100.0
    assert metrics["dag_healing_success_pct"] == 100.0

    run_id = metrics["run_id"]

    # Query evaluation list
    list_resp = client.get("/api/evaluations", headers=viewer_headers)
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert any(r["id"] == run_id for r in runs)

    # Query specific evaluation
    get_resp = client.get(f"/api/evaluations/{run_id}", headers=viewer_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id


def test_audit_trail_recorded_and_retrievable(client: TestClient, admin_headers):
    """Verify system mutations generate audit records retrievable by admin."""
    logs_resp = client.get("/api/audit/logs?limit=10", headers=admin_headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "action" in logs[0]
    assert "timestamp" in logs[0]
