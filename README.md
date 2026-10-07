# Integrated EHR Access-Control Framework

This project is an academic prototype developed for the MSIT Capstone Project. It demonstrates an integrated access-control framework for Electronic Health Records (EHRs) in a Saudi government hospital environment.

The prototype evaluates access requests using role-based and contextual security controls. It uses synthetic data only and does not connect to any real hospital system or patient record.

## Core Features

- Role-Based Access Control (RBAC) for six healthcare and technical roles.
- Context-aware checks based on authentication, account status, duty status, patient assignment, network, and device trust.
- Adaptive Multi-Factor Authentication (MFA) for high-risk access requests.
- Break-glass emergency access for authorized clinical users with mandatory justification.
- Tamper-evident audit events protected with HMAC-SHA256 checksums.
- Clear access decisions: permit, deny, require MFA, or grant emergency access.

## Supported Roles

1. Physician
2. Nurse
3. Pharmacist
4. Laboratory Technician
5. Health Information Manager
6. IT Systems Administrator

## Project Structure

```text
src/access_control_engine.py   Core access-control logic
tests/test_access_control.py   Unit tests
demo.py                        Demonstration scenarios
requirements.txt               Testing dependency
```

## Requirements

- Python 3.12 or later
- PyTest 9.0.1

## Installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the Demonstration

```powershell
.\.venv\Scripts\python.exe .\demo.py
```

## Run the Unit Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The current test suite contains 15 unit tests covering permitted access, denied access, adaptive MFA, emergency access, contextual restrictions, and audit-integrity verification.

## Ethical and Security Notice

This repository contains no real patient information, employee credentials, or hospital data. All users, patients, roles, and access scenarios are fictional and created exclusively for academic testing. The prototype is not intended for production deployment without additional security review, integration testing, and organizational approval.

## Author

Taghreed Almirabi  
MSIT 5910-01: MSIT Capstone Project  
University of the People  
AY2027-T1