"""Tests for Chat DAG structural integrity, cycle detection, and orphan healing."""

import pytest
from app.services.chat_dag import ChatDagEngine


def test_valid_chat_dag_validation():
    """Ensure a well-formed conversation DAG passes integrity checks."""
    valid_chat = {
        "id": "valid-1",
        "history": {
            "messages": {
                "m-1": {"id": "m-1", "parentId": None, "childrenIds": ["m-2"], "role": "user", "content": "Question", "timestamp": 10},
                "m-2": {"id": "m-2", "parentId": "m-1", "childrenIds": [], "role": "assistant", "content": "Answer", "timestamp": 20},
            },
            "currentId": "m-2"
        },
        "messages": [
            {"id": "m-1", "parentId": None, "content": "Question", "role": "user"},
            {"id": "m-2", "parentId": "m-1", "content": "Answer", "role": "assistant"},
        ]
    }
    report = ChatDagEngine.validate_graph(valid_chat)
    assert report.is_valid is True
    assert report.cycles_detected is False
    assert len(report.orphan_messages) == 0
    assert report.out_of_sync_count == 0


def test_cycle_detection():
    """Ensure cyclic parent-child links are detected as invalid."""
    cyclic_chat = {
        "id": "cyclic-1",
        "history": {
            "messages": {
                "c-1": {"id": "c-1", "parentId": "c-2", "childrenIds": ["c-2"], "content": "Cycle A"},
                "c-2": {"id": "c-2", "parentId": "c-1", "childrenIds": ["c-1"], "content": "Cycle B"},
            },
            "currentId": "c-2"
        }
    }
    report = ChatDagEngine.validate_graph(cyclic_chat)
    assert report.is_valid is False
    assert report.cycles_detected is True


def test_orphan_message_detection():
    """Ensure messages referencing nonexistent parents are flagged as orphans."""
    orphan_chat = {
        "id": "orphan-1",
        "history": {
            "messages": {
                "o-1": {"id": "o-1", "parentId": None, "childrenIds": [], "content": "Root", "timestamp": 10},
                "o-2": {"id": "o-2", "parentId": "ghost-parent-99", "childrenIds": [], "content": "Detached", "timestamp": 20},
            },
            "currentId": "o-2"
        }
    }
    report = ChatDagEngine.validate_graph(orphan_chat)
    assert report.is_valid is False
    assert "o-2" in report.orphan_messages


def test_repair_graph_heals_cycles_and_orphans():
    """Verify that repair_graph clears cycles, reconnects orphans, and restores validity."""
    corrupt_chat = {
        "id": "repair-test",
        "history": {
            "messages": {
                "node-a": {"id": "node-a", "parentId": "node-b", "content": "Turn A", "timestamp": 10},
                "node-b": {"id": "node-b", "parentId": "node-a", "content": "Turn B", "timestamp": 20},
                "node-orphan": {"id": "node-orphan", "parentId": "missing-parent", "content": "Orphan", "timestamp": 30},
            },
            "currentId": "node-orphan"
        },
        "messages": []
    }
    repaired_chat, report = ChatDagEngine.repair_graph(corrupt_chat)
    assert report.repaired is True
    assert report.is_valid is True
    assert report.cycles_detected is False
    assert len(report.orphan_messages) == 0

    # Ensure childrenIds are bidirectionally consistent
    repaired_nodes = repaired_chat["history"]["messages"]
    for nid, node in repaired_nodes.items():
        pid = node.get("parentId")
        if pid:
            assert nid in repaired_nodes[pid]["childrenIds"]


def test_linearize_trajectory():
    """Verify reverse traversal from leaf to root produces sequential turns."""
    chat = {
        "id": "line-1",
        "history": {
            "messages": {
                "step-1": {"id": "step-1", "parentId": None, "content": "First", "role": "user", "timestamp": 1},
                "step-2": {"id": "step-2", "parentId": "step-1", "content": "Second", "role": "assistant", "timestamp": 2},
                "step-3": {"id": "step-3", "parentId": "step-2", "content": "Third", "role": "user", "timestamp": 3},
            },
            "currentId": "step-3"
        }
    }
    trajectory = ChatDagEngine.linearize_trajectory(chat)
    assert len(trajectory) == 3
    assert trajectory[0]["id"] == "step-1"
    assert trajectory[1]["id"] == "step-2"
    assert trajectory[2]["id"] == "step-3"


def test_empty_chat_handling():
    """Ensure empty chat payloads do not raise exceptions."""
    report = ChatDagEngine.validate_graph({})
    assert report.is_valid is True
    assert report.total_messages == 0
    trajectory = ChatDagEngine.linearize_trajectory({})
    assert trajectory == []
