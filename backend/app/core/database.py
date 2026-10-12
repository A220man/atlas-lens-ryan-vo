"""SQLite transactional persistence and audit logging layer.

Uses parameterized SQL queries for injection safety, strict UTC timestamps,
pagination, filtering, and transactional guarantees.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional
import uuid

from app.core.config import Settings, get_settings


def get_db_path(db_url: str) -> str:
    """Extract SQLite path from connection URL."""
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
        if path == ":memory:":
            return path
        # Ensure parent directory exists
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        return path
    return "atlas_lens.db"


_SHARED_MEM_CONN: Optional[sqlite3.Connection] = None


@contextmanager
def get_db_connection(settings: Optional[Settings] = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield a managed SQLite connection with WAL mode and foreign keys enabled."""
    global _SHARED_MEM_CONN
    if settings is None:
        settings = get_settings()

    db_path = get_db_path(settings.database_url)
    if db_path == ":memory:":
        if _SHARED_MEM_CONN is None:
            _SHARED_MEM_CONN = sqlite3.connect(":memory:", check_same_thread=False)
            _SHARED_MEM_CONN.row_factory = sqlite3.Row
            _SHARED_MEM_CONN.execute("PRAGMA foreign_keys = ON;")
        conn = _SHARED_MEM_CONN
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return

    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(settings: Optional[Settings] = None) -> None:
    """Initialize schema tables, constraints, and audit log tables."""
    with get_db_connection(settings) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            data_json TEXT NOT NULL,
            total_messages INTEGER NOT NULL DEFAULT 0,
            is_repaired INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            details_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mcp_servers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            global_headers_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_mcp_headers (
            id TEXT PRIMARY KEY,
            server_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            header_key TEXT NOT NULL,
            header_value_masked TEXT NOT NULL,
            header_value_encrypted TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(server_id, user_id, header_key),
            FOREIGN KEY (server_id) REFERENCES mcp_servers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS evaluations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            results_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_user_mcp ON user_mcp_headers(server_id, user_id);
        """)


def record_audit_log(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
    conn: Optional[sqlite3.Connection] = None,
    settings: Optional[Settings] = None
) -> str:
    """Append an immutable audit log entry."""
    entry_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()
    clean_details = json.dumps(details)

    if conn is not None:
        conn.execute(
            """
            INSERT INTO audit_logs (id, timestamp, user_id, action, resource_type, resource_id, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_id, now_utc, user_id, action, resource_type, resource_id, clean_details)
        )
    else:
        with get_db_connection(settings) as managed_conn:
            managed_conn.execute(
                """
                INSERT INTO audit_logs (id, timestamp, user_id, action, resource_type, resource_id, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, now_utc, user_id, action, resource_type, resource_id, clean_details)
            )

    return entry_id


def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    settings: Optional[Settings] = None
) -> List[Dict[str, Any]]:
    """Retrieve audit trail logs in reverse chronological order."""
    with get_db_connection(settings) as conn:
        cursor = conn.execute(
            """
            SELECT id, timestamp, user_id, action, resource_type, resource_id, details_json
            FROM audit_logs
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "user_id": r["user_id"],
                "action": r["action"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "details": json.loads(r["details_json"]),
            }
            for r in rows
        ]
