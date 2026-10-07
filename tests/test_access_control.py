"""Unit tests for the EHR access-control engine."""

from src.access_control_engine import (
    AccessAction,
    AccessControlEngine,
    AccessDecision,
    AccessRequest,
    UserRole,
)


def physician_request(**changes) -> AccessRequest:
    values = {
        "user_id": "DR-TEST",
        "role": UserRole.PHYSICIAN,
        "action": AccessAction.VIEW_PATIENT_RECORD,
        "patient_id": "PAT-TEST",
        "assigned_to_patient": True,
    }
    values.update(changes)
    return AccessRequest(**values)


def test_assigned_physician_is_permitted():
    engine = AccessControlEngine()
    result = engine.evaluate(physician_request())
    assert result.decision == AccessDecision.PERMIT


def test_unauthenticated_user_is_denied():
    engine = AccessControlEngine()
    result = engine.evaluate(
        physician_request(authenticated=False)
    )
    assert result.decision == AccessDecision.DENY


def test_inactive_account_is_denied():
    engine = AccessControlEngine()
    result = engine.evaluate(
        physician_request(account_active=False)
    )
    assert result.decision == AccessDecision.DENY


def test_unassigned_nurse_is_denied():
    engine = AccessControlEngine()

    request = AccessRequest(
        user_id="NR-TEST",
        role=UserRole.NURSE,
        action=AccessAction.VIEW_PATIENT_RECORD,
        patient_id="PAT-TEST",
        assigned_to_patient=False,
    )

    result = engine.evaluate(request)
    assert result.decision == AccessDecision.DENY


def test_patient_identifier_is_required():
    engine = AccessControlEngine()
    result = engine.evaluate(
        physician_request(patient_id=None)
    )
    assert result.decision == AccessDecision.DENY


def test_it_administrator_cannot_view_clinical_record():
    engine = AccessControlEngine()

    request = AccessRequest(
        user_id="IT-TEST",
        role=UserRole.IT_SYSTEMS_ADMINISTRATOR,
        action=AccessAction.VIEW_PATIENT_RECORD,
        patient_id="PAT-TEST",
    )

    result = engine.evaluate(request)
    assert result.decision == AccessDecision.DENY


def test_access_outside_duty_period_is_denied():
    engine = AccessControlEngine()
    result = engine.evaluate(
        physician_request(on_duty=False)
    )
    assert result.decision == AccessDecision.DENY


def test_off_network_access_requires_mfa():
    engine = AccessControlEngine()

    result = engine.evaluate(
        physician_request(
            on_hospital_network=False,
            mfa_verified=False,
        )
    )

    assert result.decision == AccessDecision.STEP_UP_MFA


def test_unmanaged_device_requires_mfa():
    engine = AccessControlEngine()

    result = engine.evaluate(
        physician_request(
            managed_device=False,
            mfa_verified=False,
        )
    )

    assert result.decision == AccessDecision.STEP_UP_MFA


def test_high_risk_export_requires_mfa():
    engine = AccessControlEngine()

    request = AccessRequest(
        user_id="HIM-TEST",
        role=UserRole.HEALTH_INFORMATION_MANAGER,
        action=AccessAction.EXPORT_PATIENT_RECORD,
        patient_id="PAT-TEST",
        mfa_verified=False,
    )

    result = engine.evaluate(request)
    assert result.decision == AccessDecision.STEP_UP_MFA


def test_high_risk_export_is_permitted_after_mfa():
    engine = AccessControlEngine()

    request = AccessRequest(
        user_id="HIM-TEST",
        role=UserRole.HEALTH_INFORMATION_MANAGER,
        action=AccessAction.EXPORT_PATIENT_RECORD,
        patient_id="PAT-TEST",
        mfa_verified=True,
    )

    result = engine.evaluate(request)
    assert result.decision == AccessDecision.PERMIT


def test_valid_break_glass_access_is_granted():
    engine = AccessControlEngine()

    result = engine.evaluate(
        physician_request(
            assigned_to_patient=False,
            emergency=True,
            emergency_justification=(
                "Immediate lifesaving treatment is required."
            ),
        )
    )

    assert result.decision == AccessDecision.BREAK_GLASS_PERMIT
    assert result.break_glass_expires_at is not None


def test_break_glass_is_denied_for_nonclinical_role():
    engine = AccessControlEngine()

    request = AccessRequest(
        user_id="IT-TEST",
        role=UserRole.IT_SYSTEMS_ADMINISTRATOR,
        action=AccessAction.VIEW_PATIENT_RECORD,
        patient_id="PAT-TEST",
        emergency=True,
        emergency_justification=(
            "Emergency access requested for patient care."
        ),
    )

    result = engine.evaluate(request)
    assert result.decision == AccessDecision.DENY


def test_break_glass_requires_justification():
    engine = AccessControlEngine()

    result = engine.evaluate(
        physician_request(
            assigned_to_patient=False,
            emergency=True,
            emergency_justification="",
        )
    )

    assert result.decision == AccessDecision.DENY


def test_audit_checksum_detects_tampering():
    engine = AccessControlEngine()
    engine.evaluate(physician_request())

    original = engine.audit_log[-1]
    altered = engine.simulate_audit_tampering(original)

    assert engine.verify_audit_event(original) is True
    assert engine.verify_audit_event(altered) is False