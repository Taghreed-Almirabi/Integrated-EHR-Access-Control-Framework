"""Run synthetic access-control scenarios for the capstone prototype."""

from src.access_control_engine import (
    AccessAction,
    AccessControlEngine,
    AccessRequest,
    UserRole,
)


def display_result(
    name: str,
    engine: AccessControlEngine,
    request: AccessRequest,
) -> None:
    result = engine.evaluate(request)

    print("\n" + "=" * 72)
    print(f"SCENARIO: {name}")
    print(f"USER: {request.user_id}")
    print(f"ROLE: {request.role.value}")
    print(f"ACTION: {request.action.value}")
    print(f"DECISION: {result.decision.value}")
    print(f"REASON: {result.reason}")
    print(f"AUDIT EVENT: {result.audit_event_id}")

    if result.break_glass_expires_at:
        print(
            f"EMERGENCY ACCESS EXPIRES: "
            f"{result.break_glass_expires_at}"
        )


def main() -> None:
    engine = AccessControlEngine()

    scenarios = [
        (
            "Assigned physician views a patient record",
            AccessRequest(
                user_id="DR-1001",
                role=UserRole.PHYSICIAN,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PAT-2001",
                department="Emergency Medicine",
                assigned_to_patient=True,
            ),
        ),
        (
            "Unassigned nurse attempts to view a patient record",
            AccessRequest(
                user_id="NR-1002",
                role=UserRole.NURSE,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PAT-2002",
                department="Medical Ward",
                assigned_to_patient=False,
            ),
        ),
        (
            "Health information manager requests a high-risk export",
            AccessRequest(
                user_id="HIM-1003",
                role=UserRole.HEALTH_INFORMATION_MANAGER,
                action=AccessAction.EXPORT_PATIENT_RECORD,
                patient_id="PAT-2003",
                department="Health Information Management",
                mfa_verified=False,
            ),
        ),
        (
            "Physician activates emergency break-glass access",
            AccessRequest(
                user_id="DR-1004",
                role=UserRole.PHYSICIAN,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PAT-2004",
                department="Emergency Medicine",
                assigned_to_patient=False,
                emergency=True,
                emergency_justification=(
                    "Immediate treatment is required "
                    "to protect the patient."
                ),
            ),
        ),
        (
            "IT administrator attempts to access clinical information",
            AccessRequest(
                user_id="IT-1005",
                role=UserRole.IT_SYSTEMS_ADMINISTRATOR,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PAT-2005",
                department="Digital Health",
                mfa_verified=True,
            ),
        ),
    ]

    print("INTEGRATED EHR ACCESS-CONTROL FRAMEWORK")
    print("Synthetic demonstration data only")

    for name, request in scenarios:
        display_result(name, engine, request)

    original_event = engine.audit_log[-1]
    altered_event = engine.simulate_audit_tampering(original_event)

    print("\n" + "=" * 72)
    print("AUDIT INTEGRITY CHECK")
    print(
        "ORIGINAL EVENT VALID:",
        engine.verify_audit_event(original_event),
    )
    print(
        "ALTERED EVENT VALID:",
        engine.verify_audit_event(altered_event),
    )
    print("TOTAL AUDIT EVENTS:", len(engine.audit_log))


if __name__ == "__main__":
    main()