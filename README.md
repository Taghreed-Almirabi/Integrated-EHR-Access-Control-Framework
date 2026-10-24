# Integrated EHR Access-Control Framework

Academic prototype developed for the MSIT Capstone Project (MSIT 5910, University of the People). It demonstrates an integrated access-control framework for Electronic Health Records (EHRs) in a modeled Saudi government hospital: role-based access control, contextual authorization, step-up multifactor authentication, controlled break-glass emergency access, and tamper-evident audit logging behind one application service.

The prototype uses synthetic data only. It does not connect to any real hospital system, identity provider, or patient record.

Project portfolio: https://taghreed-almirabi.github.io/capstone-portfolio/

## Core Features

- Role-Based Access Control (RBAC) for six healthcare and technical roles.
- Context-aware checks: account status, authentication, duty status, patient assignment, network location, and device trust.
- Step-up multifactor authentication (STEP_UP_MFA) for high-risk actions and contexts.
- Break-glass emergency access for clinical roles, with a mandatory justification and a 15-minute expiry.
- One HMAC-SHA256-signed audit event for every decision, including denials, persisted in SQLite.
- Four decisions: PERMIT, DENY, STEP_UP_MFA, BREAK_GLASS_PERMIT, each with a human-readable reason.

## Supported Roles

1. Physician
2. Nurse
3. Pharmacist
4. Laboratory Technician
5. Health Information Manager
6. IT Systems Administrator

## Project Structure

```text
src/access_control_engine.py          Policy decision point: RBAC, context, MFA, break-glass, audit signing
src/ehr_access_service.py             Service layer coordinating authorization and persistence
src/audit_repository.py               SQLite audit repository
tests/test_access_control.py          15 unit tests
tests/test_system_integration.py      3 integration tests
tests/test_unit7_system_acceptance.py 7 system, acceptance, and stability tests
demo.py                               Scenario demonstration (in-memory)
system_demo.py                        End-to-end demonstration with persisted audit events
performance_evaluation.py             36-case decision benchmark, latency percentiles, memory, clarity review
results/                              Evaluation outputs (CSV, environment JSON, chart, test log)
deployment/DEPLOYMENT.md              Deployment and configuration guide
docs/                                 Testing and maintenance plan
Dockerfile, .env.example              Container build and configuration template
```

## Requirements

- Python 3.12 or later
- pytest 9.1.1 and Matplotlib 3.11.2 (pinned in `requirements.txt`)

## Installation (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the Demonstrations

```powershell
.\.venv\Scripts\python.exe .\demo.py
.\.venv\Scripts\python.exe .\system_demo.py
```

## Run the Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The suite contains 25 automated tests at unit, integration, system, acceptance, and stability levels. The verbose log of the verified run is kept in `results/unit7_full_test_log.txt`.

## Run the Evaluation

```powershell
.\.venv\Scripts\python.exe .\performance_evaluation.py
```

The script checks 36 labeled scenarios (six per role) against expected decisions, measures per-request latency over 300 timed requests after 10 warm-up requests (mean, median, p95, p99), throughput, and peak memory, records the benchmark environment, and writes `results/evaluation_results.csv`, `results/evaluation_environment.json`, and `results/system_evaluation_chart.png`.

## Releases

| Tag | Content |
| --- | --- |
| v0.1.0-core | Core access-control engine |
| v0.2.0-tested | Unit tests |
| v1.0.0 | Documented release |
| v1.1.0-unit6 | Integration, evaluation, deployment plan |
| v1.2.0-unit7 | System and acceptance testing, maintenance plan |
| v1.3.0-final | Final submission: 36-case benchmark, latency percentiles, environment capture |

## Ethical and Security Notice

This repository contains no real patient information, employee credentials, or hospital data. All users, patients, roles, and access scenarios are fictional and created exclusively for academic testing. The prototype is not intended for production deployment without additional security review, integration testing, and organizational approval.

## Author

Taghreed Almirabi  
MSIT 5910-01: MSIT Capstone Project  
University of the People  
AY2027-T1
