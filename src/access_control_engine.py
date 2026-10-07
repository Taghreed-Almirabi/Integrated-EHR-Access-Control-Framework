"""Context-aware access-control prototype for synthetic EHR scenarios."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import json
import secrets
from typing import Optional


class UserRole(str, Enum):
    PHYSICIAN = "physician"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    LAB_TECHNICIAN = "lab_technician"
    HEALTH_INFORMATION_MANAGER = "health_information_manager"
    IT_SYSTEMS_ADMINISTRATOR = "it_systems_administrator"


class AccessAction(str, Enum):
    VIEW_PATIENT_RECORD = "view_patient_record"
    UPDATE_CLINICAL_NOTES = "update_clinical_notes"
    PRESCRIBE_MEDICATION = "prescribe_medication"
    ADMINISTER_MEDICATION = "administer_medication"
    DISPENSE_MEDICATION = "dispense_medication"
    RECORD_LAB_RESULT = "record_lab_result"
    EXPORT_PATIENT_RECORD = "export_patient_record"
    MANAGE_USER_ACCOUNTS = "manage_user_accounts"
    REVIEW_AUDIT_LOGS = "review_audit_logs"


class AccessDecision(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    STEP_UP_MFA = "STEP_UP_MFA"
    BREAK_GLASS_PERMIT = "BREAK_GLASS_PERMIT"


@dataclass(frozen=True)
class AccessRequest:
    user_id: str
    role: UserRole
    action: AccessAction
    patient_id: Optional[str] = None
    department: str = "General"
    location: str = "Hospital"
    authenticated: bool = True
    account_active: bool = True
    on_duty: bool = True
    assigned_to_patient: bool = False
    on_hospital_network: bool = True
    managed_device: bool = True
    mfa_verified: bool = False
    emergency: bool = False
    emergency_justification: Optional[str] = None


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    timestamp: str
    user_id: str
    role: str
    action: str
    patient_id: Optional[str]
    decision: str
    reason: str
    checksum: str


@dataclass(frozen=True)
class DecisionResult:
    decision: AccessDecision
    reason: str
    audit_event_id: str
    break_glass_expires_at: Optional[str] = None


class AccessControlEngine:
    """Evaluates role, context, MFA, and emergency-access conditions."""

    PERMISSIONS = {
        UserRole.PHYSICIAN: {
            AccessAction.VIEW_PATIENT_RECORD,
            AccessAction.UPDATE_CLINICAL_NOTES,
            AccessAction.PRESCRIBE_MEDICATION,
        },
        UserRole.NURSE: {
            AccessAction.VIEW_PATIENT_RECORD,
            AccessAction.UPDATE_CLINICAL_NOTES,
            AccessAction.ADMINISTER_MEDICATION,
        },
        UserRole.PHARMACIST: {
            AccessAction.VIEW_PATIENT_RECORD,
            AccessAction.DISPENSE_MEDICATION,
        },
        UserRole.LAB_TECHNICIAN: {
            AccessAction.VIEW_PATIENT_RECORD,
            AccessAction.RECORD_LAB_RESULT,
        },
        UserRole.HEALTH_INFORMATION_MANAGER: {
            AccessAction.VIEW_PATIENT_RECORD,
            AccessAction.EXPORT_PATIENT_RECORD,
            AccessAction.REVIEW_AUDIT_LOGS,
        },
        UserRole.IT_SYSTEMS_ADMINISTRATOR: {
            AccessAction.MANAGE_USER_ACCOUNTS,
            AccessAction.REVIEW_AUDIT_LOGS,
        },
    }

    PATIENT_ACTIONS = {
        AccessAction.VIEW_PATIENT_RECORD,
        AccessAction.UPDATE_CLINICAL_NOTES,
        AccessAction.PRESCRIBE_MEDICATION,
        AccessAction.ADMINISTER_MEDICATION,
        AccessAction.DISPENSE_MEDICATION,
        AccessAction.RECORD_LAB_RESULT,
        AccessAction.EXPORT_PATIENT_RECORD,
    }

    CLINICAL_ACTIONS = {
        AccessAction.VIEW_PATIENT_RECORD,
        AccessAction.UPDATE_CLINICAL_NOTES,
        AccessAction.PRESCRIBE_MEDICATION,
        AccessAction.ADMINISTER_MEDICATION,
    }

    HIGH_RISK_ACTIONS = {
        AccessAction.EXPORT_PATIENT_RECORD,
        AccessAction.MANAGE_USER_ACCOUNTS,
    }

    def __init__(self, audit_secret: bytes = b"synthetic-capstone-key") -> None:
        self.audit_secret = audit_secret
        self.audit_log: list[AuditEvent] = []

    def evaluate(self, request: AccessRequest) -> DecisionResult:
        if not request.account_active:
            return self._finish(
                request, AccessDecision.DENY, "Account is inactive."
            )

        if not request.authenticated:
            return self._finish(
                request, AccessDecision.DENY, "Authentication is required."
            )

        if request.emergency:
            return self._evaluate_break_glass(request)

        allowed_actions = self.PERMISSIONS.get(request.role, set())

        if request.action not in allowed_actions:
            return self._finish(
                request,
                AccessDecision.DENY,
                "The requested action is not permitted for this role.",
            )

        if request.action in self.PATIENT_ACTIONS and not request.patient_id:
            return self._finish(
                request,
                AccessDecision.DENY,
                "A patient identifier is required for this action.",
            )

        if not request.on_duty:
            return self._finish(
                request,
                AccessDecision.DENY,
                "Access is outside the user's active duty period.",
            )

        if (
            request.role in {UserRole.PHYSICIAN, UserRole.NURSE}
            and request.action in self.PATIENT_ACTIONS
            and not request.assigned_to_patient
        ):
            return self._finish(
                request,
                AccessDecision.DENY,
                "The clinician is not assigned to this patient.",
            )

        elevated_risk = (
            request.action in self.HIGH_RISK_ACTIONS
            or not request.on_hospital_network
            or not request.managed_device
        )

        if elevated_risk and not request.mfa_verified:
            return self._finish(
                request,
                AccessDecision.STEP_UP_MFA,
                "Additional MFA verification is required for this context.",
            )

        return self._finish(
            request,
            AccessDecision.PERMIT,
            "Role and contextual access checks passed.",
        )

    def _evaluate_break_glass(
        self, request: AccessRequest
    ) -> DecisionResult:
        if request.role not in {UserRole.PHYSICIAN, UserRole.NURSE}:
            return self._finish(
                request,
                AccessDecision.DENY,
                "Break-glass access is limited to authorized clinical roles.",
            )

        if (
            request.action not in self.CLINICAL_ACTIONS
            or not request.patient_id
        ):
            return self._finish(
                request,
                AccessDecision.DENY,
                "Emergency access requires a patient and a clinical action.",
            )

        if (
            not request.emergency_justification
            or len(request.emergency_justification.strip()) < 10
        ):
            return self._finish(
                request,
                AccessDecision.DENY,
                "A meaningful emergency justification is required.",
            )

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        return self._finish(
            request,
            AccessDecision.BREAK_GLASS_PERMIT,
            "Temporary emergency access granted and flagged for review.",
            expires_at.isoformat(),
        )

    def _finish(
        self,
        request: AccessRequest,
        decision: AccessDecision,
        reason: str,
        expires_at: Optional[str] = None,
    ) -> DecisionResult:
        event = self._create_audit_event(request, decision, reason)
        self.audit_log.append(event)

        return DecisionResult(
            decision,
            reason,
            event.event_id,
            expires_at,
        )

    def _create_audit_event(
        self,
        request: AccessRequest,
        decision: AccessDecision,
        reason: str,
    ) -> AuditEvent:
        payload = {
            "event_id": secrets.token_hex(8),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": request.user_id,
            "role": request.role.value,
            "action": request.action.value,
            "patient_id": request.patient_id,
            "decision": decision.value,
            "reason": reason,
        }

        checksum = self._sign(payload)
        return AuditEvent(**payload, checksum=checksum)

    def _sign(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

        return hmac.new(
            self.audit_secret,
            encoded,
            hashlib.sha256,
        ).hexdigest()

    def verify_audit_event(self, event: AuditEvent) -> bool:
        payload = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "user_id": event.user_id,
            "role": event.role,
            "action": event.action,
            "patient_id": event.patient_id,
            "decision": event.decision,
            "reason": event.reason,
        }

        expected = self._sign(payload)
        return hmac.compare_digest(event.checksum, expected)

    def simulate_audit_tampering(
        self, event: AuditEvent
    ) -> AuditEvent:
        """Creates a changed copy for an integrity-check demonstration."""
        return replace(event, reason="Altered audit reason")