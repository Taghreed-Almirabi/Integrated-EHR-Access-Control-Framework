from pathlib import Path

from src.access_control_engine import (
    AccessAction,
    AccessDecision,
    AccessRequest,
    UserRole,
)
from src.audit_repository import AuditRepository
from src.ehr_access_service import EHRAccessService


def test_blank_user_id_is_denied_and_audited(tmp_path: Path) -> None:
    """Verify that a request without a valid user ID is rejected."""
    repository = AuditRepository(tmp_path / "unit7_audit.db")
    service = EHRAccessService(repository=repository)

    request = AccessRequest(
        user_id="   ",
        role=UserRole.PHYSICIAN,
        action=AccessAction.VIEW_PATIENT_RECORD,
        patient_id="PATIENT-U7-001",
        department="Emergency",
        location="Test Hospital",
        authenticated=True,
        account_active=True,
        on_duty=True,
        assigned_to_patient=True,
        on_hospital_network=True,
        managed_device=True,
        mfa_verified=True,
    )

    result = service.process_request(request)

    assert result.decision == AccessDecision.DENY
    assert "user identifier" in result.reason.lower()
    assert service.audit_event_count() == 1

def create_unit7_service(tmp_path: Path, database_name: str) -> EHRAccessService:
    """Create an isolated integrated service for one system scenario."""
    repository = AuditRepository(tmp_path / database_name)
    return EHRAccessService(repository=repository)


def make_unit7_request(**overrides) -> AccessRequest:
    """Build a valid request that each scenario can adjust."""
    values = {
        "user_id": "DR-U7-001",
        "role": UserRole.PHYSICIAN,
        "action": AccessAction.VIEW_PATIENT_RECORD,
        "patient_id": "PATIENT-U7-001",
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


def test_acceptance_authorized_physician_is_permitted(tmp_path: Path) -> None:
    """Confirm the normal physician workflow from request to database."""
    service = create_unit7_service(tmp_path, "physician_acceptance.db")

    result = service.process_request(make_unit7_request())
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.PERMIT
    assert service.audit_event_count() == 1
    assert records[0]["user_id"] == "DR-U7-001"
    assert records[0]["decision"] == "PERMIT"


def test_acceptance_high_risk_export_requires_mfa(tmp_path: Path) -> None:
    """Confirm that export is paused until additional MFA is completed."""
    service = create_unit7_service(tmp_path, "mfa_acceptance.db")
    request = make_unit7_request(
        user_id="HIM-U7-001",
        role=UserRole.HEALTH_INFORMATION_MANAGER,
        action=AccessAction.EXPORT_PATIENT_RECORD,
        assigned_to_patient=False,
        mfa_verified=False,
    )

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.STEP_UP_MFA
    assert records[0]["decision"] == "STEP_UP_MFA"


def test_acceptance_break_glass_is_time_limited_and_audited(
    tmp_path: Path,
) -> None:
    """Confirm emergency access, expiry information, and persistence."""
    service = create_unit7_service(tmp_path, "break_glass_acceptance.db")
    request = make_unit7_request(
        user_id="NURSE-U7-ER",
        role=UserRole.NURSE,
        assigned_to_patient=False,
        mfa_verified=False,
        emergency=True,
        emergency_justification=(
            "Immediate access is required for lifesaving treatment."
        ),
    )

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.BREAK_GLASS_PERMIT
    assert result.break_glass_expires_at is not None
    assert records[0]["decision"] == "BREAK_GLASS_PERMIT"


def test_acceptance_it_admin_is_denied_clinical_access(tmp_path: Path) -> None:
    """Confirm separation between technical and clinical duties."""
    service = create_unit7_service(tmp_path, "admin_acceptance.db")
    request = make_unit7_request(
        user_id="IT-U7-001",
        role=UserRole.IT_SYSTEMS_ADMINISTRATOR,
        assigned_to_patient=False,
    )

    result = service.process_request(request)
    records = service.recent_audit_events(limit=1)

    assert result.decision == AccessDecision.DENY
    assert records[0]["decision"] == "DENY"


def test_system_mixed_workflow_creates_complete_audit_trail(
    tmp_path: Path,
) -> None:
    """Exercise permit, deny, MFA, and emergency decisions together."""
    service = create_unit7_service(tmp_path, "mixed_system.db")
    requests = [
        make_unit7_request(),
        make_unit7_request(
            user_id="NURSE-U7-002",
            role=UserRole.NURSE,
            assigned_to_patient=False,
        ),
        make_unit7_request(
            user_id="HIM-U7-002",
            role=UserRole.HEALTH_INFORMATION_MANAGER,
            action=AccessAction.EXPORT_PATIENT_RECORD,
            assigned_to_patient=False,
            mfa_verified=False,
        ),
        make_unit7_request(
            user_id="NURSE-U7-003",
            role=UserRole.NURSE,
            assigned_to_patient=False,
            emergency=True,
            emergency_justification="Emergency patient intervention required.",
        ),
    ]

    results = [service.process_request(request) for request in requests]
    records = service.recent_audit_events(limit=10)

    expected = {
        AccessDecision.PERMIT,
        AccessDecision.DENY,
        AccessDecision.STEP_UP_MFA,
        AccessDecision.BREAK_GLASS_PERMIT,
    }
    assert {result.decision for result in results} == expected
    assert {record["decision"] for record in records} == {
        decision.value for decision in expected
    }
    assert service.audit_event_count() == 4


def test_stability_fifty_requests_are_processed_without_loss(
    tmp_path: Path,
) -> None:
    """Confirm that repeated requests remain complete and traceable."""
    service = create_unit7_service(tmp_path, "stability_system.db")

    results = [
        service.process_request(
            make_unit7_request(user_id=f"DR-STABILITY-{index:03d}")
        )
        for index in range(50)
    ]
    event_ids = [result.audit_event_id for result in results]

    assert all(result.decision == AccessDecision.PERMIT for result in results)
    assert service.audit_event_count() == 50
    assert len(set(event_ids)) == 50