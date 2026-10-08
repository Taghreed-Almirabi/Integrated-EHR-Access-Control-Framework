from __future__ import annotations

from .access_control_engine import (
    AccessControlEngine,
    AccessRequest,
    AuditEvent,
    DecisionResult,
)
from .audit_repository import AuditRepository


class EHRAccessService:
    """Coordinate access decisions and persistent audit logging."""

    def __init__(
        self,
        engine: AccessControlEngine | None = None,
        repository: AuditRepository | None = None,
    ) -> None:
        self.engine = engine or AccessControlEngine()
        self.repository = repository or AuditRepository()

    def process_request(
        self,
        request: AccessRequest,
    ) -> DecisionResult:
        """Evaluate one request and store its audit event."""
        result = self.engine.evaluate(request)
        event = self._find_audit_event(result.audit_event_id)
        self.repository.save_event(event)
        return result

    def _find_audit_event(
        self,
        event_id: str,
    ) -> AuditEvent:
        """Find the audit event created for a decision."""
        for event in reversed(self.engine.audit_log):
            if str(event.event_id) == str(event_id):
                return event

        raise LookupError(
            f"Audit event was not found: {event_id}"
        )

    def audit_event_count(self) -> int:
        """Return the number of persisted events."""
        return self.repository.count_events()

    def recent_audit_events(
        self,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Return recent events from the database."""
        return self.repository.get_recent_events(limit)