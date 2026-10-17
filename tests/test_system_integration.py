from pathlib import Path

from src.access_control_engine import (
    AccessAction,
    AccessDecision,
    AccessRequest,
    UserRole,
)
from src.audit_repository import AuditRepository
from src.ehr_access_service import EHRAccessService


def create_service(tmp_path: Path) -> EHRAccessService:
    """Create an integrated service with a temporary test database."""
    repository = AuditRepository(tmp_path / "test_audit.db")
    return EHRAccessService(repository=repository)


def make_request(**overrides) -> AccessRequest:
    """Create a valid default request that tests may modify."""
    values = {
        "user_id": "DR-TEST",
        "role": UserRole.PHYSICIAN,
        "action": AccessAction.VIEW_PATIENT_RECORD,
        "patient_id": "PATIENT-TEST",
        "department": "Emergency",
        "location": "Test Hospital",
        "authenticated": True,
        "account_active": True,
        "on_duty": True,
        "assigned_to_patient": True,
        "on_hospital_network": True,
        "managed_device": True,
        "mfa_verified": True,
    }

    values.update(overrides)
    return AccessRequest(**values)


def test_permitted_request_is_saved(tmp_path: Path) -> None:
    """Verify that an authorized decision is persisted."""
    service = create_service(tmp_path)
    request = make_request()

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.PERMIT
    assert service.audit_event_count() == 1
    assert records[0]["user_id"] == "DR-TEST"
    assert records[0]["decision"] == "PERMIT"


def test_denied_request_is_saved(tmp_path: Path) -> None:
    """Verify that an unauthenticated request is denied and persisted."""
    service = create_service(tmp_path)
    request = make_request(
        user_id="NURSE-TEST",
        role=UserRole.NURSE,
        action=AccessAction.ADMINISTER_MEDICATION,
        authenticated=False,
    )

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.DENY
    assert service.audit_event_count() == 1
    assert records[0]["user_id"] == "NURSE-TEST"
    assert records[0]["decision"] == "DENY"


def test_break_glass_request_is_saved(tmp_path: Path) -> None:
    """Verify emergency access and its database audit record."""
    service = create_service(tmp_path)
    request = make_request(
        user_id="NURSE-ER-TEST",
        role=UserRole.NURSE,
        assigned_to_patient=False,
        emergency=True,
        emergency_justification=(
            "Immediate access is required for emergency patient care."
        ),
    )

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.BREAK_GLASS_PERMIT
    assert service.audit_event_count() == 1
    assert records[0]["user_id"] == "NURSE-ER-TEST"
    assert records[0]["decision"] == "BREAK_GLASS_PERMIT"