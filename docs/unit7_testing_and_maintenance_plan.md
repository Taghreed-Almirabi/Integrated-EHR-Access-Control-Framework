# Unit 7 System Testing and Maintenance Plan

## Project Overview

The project, titled **Designing and Evaluating an Integrated Access Control Framework for Electronic Health Records in a Saudi Government Hospital**, provides a prototype for controlling access to electronic health record data. The system combines role-based access control, contextual policy checks, multifactor authentication requirements, emergency break-glass access, and audit logging. It uses synthetic data only and does not connect to a real hospital system or process identifiable patient information.

This document records the comprehensive testing completed during Unit 7 and presents a proposed maintenance plan for the system after deployment.

## 1. System Testing and Documentation

### 1.1 Testing Objectives and Scope

The testing process was designed to verify that the integrated access-control system:

- Permits authorized clinical activities.
- Denies unauthorized or invalid requests.
- applies step-up multifactor authentication to high-risk actions.
- Supports controlled and time-limited emergency access.
- Records access decisions in the audit repository.
- Maintains consistent behavior after the addition of new validation logic.
- Processes repeated requests without losing audit records.

Testing covered the access-control engine, role and contextual policy rules, authentication status, emergency-access logic, and audit repository. The tests were performed locally with fictional users, roles, patients, and access requests.

### 1.2 Test Environment

| Item | Configuration |
|---|---|
| Operating system | Microsoft Windows |
| Programming language | Python 3.12.15 |
| Testing framework | PyTest 9.1.1 |
| Data source | Synthetic test data |
| Audit storage | Local SQLite repository |
| Version control | Git and GitHub |
| Development environment | Visual Studio Code and Python virtual environment |

### 1.3 Levels and Types of Testing

| Test level | Purpose | Testing approach | Evidence |
|---|---|---|---|
| Unit testing | Verify individual access rules and decision logic | Mainly white-box testing | `tests/test_access_control.py` |
| Integration testing | Verify communication between the policy engine, authentication logic, and audit repository | White-box and interface testing | `tests/test_system_integration.py` |
| System testing | Verify the behavior of the complete integrated prototype | Black-box scenario testing | `tests/test_unit7_system_acceptance.py` |
| Acceptance testing | Confirm that representative healthcare workflows satisfy the project requirements | Requirements-based black-box testing | `tests/test_unit7_system_acceptance.py` |
| Stability testing | Process multiple requests and confirm that no audit events are lost | Repeated-workload testing | `test_repeated_requests_are_processed_without_audit_loss` |

White-box testing was used when the internal branches and policy conditions were known and examined directly. Black-box testing evaluated the system through inputs and expected outputs without depending on the internal implementation details.

### 1.4 Test Procedures

The Unit 7 system and acceptance tests were executed with:

```powershell
python -m pytest tests/test_unit7_system_acceptance.py -v