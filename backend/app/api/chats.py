"""Chat DAG management, validation, repair, and export endpoints.

Enforces role authorization on all routes.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db_connection, record_audit_log
from app.core.security import get_current_user, require_role
from app.models.schemas import ChatRecord, ChatValidationReport, User
from app.services.chat_dag import ChatDagEngine

router = APIRouter(prefix="/api/chats", tags=["Chat DAGs"])


@router.get("", response_model=List[ChatRecord])
def list_chats(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role("viewer"))
) -> List[ChatRecord]:
    """List persisted chats with integrity summaries."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, user_id, title, data_json, total_messages, is_repaired, created_at, updated_at
            FROM chats
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = cursor.fetchall()
        results: List[ChatRecord] = []
        for r in rows:
            chat_data = json.loads(r["data_json"])
            val_report = ChatDagEngine.validate_graph(chat_data)
            results.append(
                ChatRecord(
                    id=r["id"],
                    title=r["title"],
                    user_id=r["user_id"],
                    total_messages=r["total_messages"],
                    is_repaired=bool(r["is_repaired"]),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    validation_summary=val_report
                )
            )
        return results


@router.post("/import", response_model=Dict[str, Any])
def import_chat(
    payload: Dict[str, Any],
    auto_repair: bool = Query(True),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """Import and validate conversational tree data.

    Addresses Issue #15189: Validates structural integrity and repairs
    orphan messages or cycles before database persistence.
    """
    chat_id = payload.get("id") or str(uuid.uuid4())
    title = payload.get("title") or "Imported Session"
    now_utc = datetime.now(timezone.utc).isoformat()

    # Initial validation
    initial_report = ChatDagEngine.validate_graph(payload)

    repaired_flag = 0
    final_data = payload
    final_report = initial_report

    if not initial_report.is_valid and auto_repair:
        final_data, final_report = ChatDagEngine.repair_graph(payload)
        repaired_flag = 1
    elif not initial_report.is_valid and not auto_repair:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Chat tree failed structural validation.",
                "report": initial_report.model_dump()
            }
        )

    nodes = ChatDagEngine.extract_nodes(final_data)

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO chats (id, user_id, title, data_json, total_messages, is_repaired, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                data_json = excluded.data_json,
                total_messages = excluded.total_messages,
                is_repaired = excluded.is_repaired,
                updated_at = excluded.updated_at
            """,
            (
                chat_id,
                current_user.id,
                title,
                json.dumps(final_data),
                len(nodes),
                repaired_flag,
                now_utc,
                now_utc
            )
        )
        record_audit_log(
            user_id=current_user.id,
            action="IMPORT_CHAT",
            resource_type="chat",
            resource_id=chat_id,
            details={"is_repaired": bool(repaired_flag), "total_messages": len(nodes)},
            conn=conn
        )

    return {
        "id": chat_id,
        "title": title,
        "total_messages": len(nodes),
        "is_repaired": bool(repaired_flag),
        "validation_report": final_report.model_dump()
    }


@router.get("/{chat_id}")
def get_chat(
    chat_id: str,
    current_user: User = Depends(require_role("viewer"))
) -> Dict[str, Any]:
    """Retrieve full chat details, DAG graph, and linearized trajectory."""
    with get_db_connection() as conn:
        cur = conn.execute("SELECT id, user_id, title, data_json, is_repaired, created_at, updated_at FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")

        raw_data = json.loads(row["data_json"])
        report = ChatDagEngine.validate_graph(raw_data)
        trajectory = ChatDagEngine.linearize_trajectory(raw_data)

        return {
            "id": row["id"],
            "title": row["title"],
            "user_id": row["user_id"],
            "is_repaired": bool(row["is_repaired"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "validation_report": report.model_dump(),
            "chat_data": raw_data,
            "linearized_trajectory": trajectory
        }


@router.post("/{chat_id}/repair")
def repair_chat(
    chat_id: str,
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """Force structural healing on an existing persisted chat."""
    with get_db_connection() as conn:
        cur = conn.execute("SELECT data_json, title FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")

        raw_data = json.loads(row["data_json"])
        repaired_data, report = ChatDagEngine.repair_graph(raw_data)
        now_utc = datetime.now(timezone.utc).isoformat()
        nodes = ChatDagEngine.extract_nodes(repaired_data)

        conn.execute(
            """
            UPDATE chats
            SET data_json = ?, total_messages = ?, is_repaired = 1, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(repaired_data), len(nodes), now_utc, chat_id)
        )
        record_audit_log(
            user_id=current_user.id,
            action="REPAIR_CHAT",
            resource_type="chat",
            resource_id=chat_id,
            details={"orphan_repaired": len(report.orphan_messages)},
            conn=conn
        )

        return {
            "id": chat_id,
            "status": "repaired",
            "report": report.model_dump()
        }


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: str,
    current_user: User = Depends(require_role("admin"))
) -> Dict[str, str]:
    """Delete a chat record (admin only)."""
    with get_db_connection() as conn:
        cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")

        record_audit_log(
            user_id=current_user.id,
            action="DELETE_CHAT",
            resource_type="chat",
            resource_id=chat_id,
            details={"deleted_by": current_user.id},
            conn=conn
        )
        return {"status": "deleted", "id": chat_id}


@router.get("/{chat_id}/export")
def export_chat(
    chat_id: str,
    current_user: User = Depends(require_role("viewer"))
) -> Dict[str, Any]:
    """Export clean chat JSON with guaranteed acyclic structure."""
    with get_db_connection() as conn:
        cur = conn.execute("SELECT data_json FROM chats WHERE id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' not found.")
        return json.loads(row["data_json"])
