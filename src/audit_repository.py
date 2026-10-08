from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .access_control_engine import AuditEvent


def _as_text(value: Any) -> str:
    """Convert enum and other values into database-friendly text."""
    raw_value = getattr(value, "value", value)
    return str(raw_value)


class AuditRepository:
    """Store and retrieve access-control audit events using SQLite."""

    def __init__(
        self,
        db_path: str | Path = "data/ehr_audit.db",
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        """Create a configured SQLite connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_table(self) -> None:
        """Create the audit table and close the connection safely."""
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    checksum TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_event(self, event: AuditEvent) -> None:
        """Persist one signed audit event."""
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO audit_events (
                    event_id,
                    timestamp,
                    user_id,
                    role,
                    action,
                    patient_id,
                    decision,
                    reason,
                    checksum
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _as_text(event.event_id),
                    _as_text(event.timestamp),
                    _as_text(event.user_id),
                    _as_text(event.role),
                    _as_text(event.action),
                    _as_text(event.patient_id),
                    _as_text(event.decision),
                    _as_text(event.reason),
                    _as_text(event.checksum),
                ),
            )
            connection.commit()

    def count_events(self) -> int:
        """Return the total number of stored audit events."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM audit_events"
            ).fetchone()

        return int(row["total"])

    def get_recent_events(
        self,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Return the most recent audit events."""
        safe_limit = max(1, int(limit))

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT
                    event_id,
                    timestamp,
                    user_id,
                    role,
                    action,
                    patient_id,
                    decision,
                    reason,
                    checksum
                FROM audit_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        return [dict(row) for row in rows]