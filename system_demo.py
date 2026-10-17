from src.access_control_engine import (
    AccessAction,
    AccessRequest,
    UserRole,
)
from src.ehr_access_service import EHRAccessService


def run_scenario(
    service: EHRAccessService,
    title: str,
    request: AccessRequest,
) -> None:
    """Process and display one synthetic access request."""
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)

    print(
        "INPUT  : "
        f"user={request.user_id}, "
        f"role={request.role.value}, "
        f"action={request.action.value}, "
        f"patient={request.patient_id}, "
        f"emergency={request.emergency}"
    )

    result = service.process_request(request)

    print(f"OUTPUT : decision={result.decision.value}")
    print(f"REASON : {result.reason}")
    print(f"AUDIT  : event_id={result.audit_event_id}")


def main() -> None:
    """Run integrated EHR access-control demonstrations."""
    service = EHRAccessService()

    print("INTEGRATED EHR ACCESS CONTROL FRAMEWORK")
    print("Synthetic demonstration data only")
    print(f"Starting database events: {service.audit_event_count()}")

    scenarios = [
        (
            "Scenario 1 - Authorized physician access",
            AccessRequest(
                user_id="DR-001",
                role=UserRole.PHYSICIAN,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PATIENT-001",
                department="Emergency",
                location="Jeddah Hospital",
                authenticated=True,
                account_active=True,
                on_duty=True,
                assigned_to_patient=True,
                on_hospital_network=True,
                managed_device=True,
                mfa_verified=True,
            ),
        ),
        (
            "Scenario 2 - Authorized pharmacist action",
            AccessRequest(
                user_id="PH-001",
                role=UserRole.PHARMACIST,
                action=AccessAction.DISPENSE_MEDICATION,
                patient_id="PATIENT-002",
                department="Pharmacy",
                location="Jeddah Hospital",
                authenticated=True,
                account_active=True,
                on_duty=True,
                on_hospital_network=True,
                managed_device=True,
                mfa_verified=True,
            ),
        ),
        (
            "Scenario 3 - Unauthenticated request denied",
            AccessRequest(
                user_id="NURSE-001",
                role=UserRole.NURSE,
                action=AccessAction.ADMINISTER_MEDICATION,
                patient_id="PATIENT-003",
                department="Medical Ward",
                location="Jeddah Hospital",
                authenticated=False,
                account_active=True,
                on_duty=True,
                assigned_to_patient=True,
                on_hospital_network=True,
                managed_device=True,
                mfa_verified=True,
            ),
        ),
        (
            "Scenario 4 - Emergency break-glass access",
            AccessRequest(
                user_id="NURSE-ER-001",
                role=UserRole.NURSE,
                action=AccessAction.VIEW_PATIENT_RECORD,
                patient_id="PATIENT-004",
                department="Emergency",
                location="Jeddah Hospital",
                authenticated=True,
                account_active=True,
                on_duty=True,
                assigned_to_patient=False,
                on_hospital_network=True,
                managed_device=True,
                mfa_verified=True,
                emergency=True,
                emergency_justification=(
                    "Unconscious patient requires immediate emergency care."
                ),
            ),
        ),
    ]

    for title, request in scenarios:
        run_scenario(service, title, request)

    print("\n" + "=" * 65)
    print("DATABASE INTEGRATION SUMMARY")
    print("=" * 65)
    print(f"Final database events: {service.audit_event_count()}")

    print("\nMost recent persisted audit events:")
    for event in service.recent_audit_events(limit=4):
        print(
            f"- user={event['user_id']}, "
            f"action={event['action']}, "
            f"decision={event['decision']}"
        )


if __name__ == "__main__":
    main()