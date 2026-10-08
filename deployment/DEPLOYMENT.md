# Deployment and Configuration Guide

## 1. Deployment Options

The prototype can be executed locally with a Python virtual environment, hosted on an organization-controlled on-premise server, or packaged as a Docker container for deployment to a private cloud platform. Local execution is suitable for development and testing, while an on-premise server offers direct organizational control. A private cloud environment provides greater portability and scalability but requires secure network and identity configuration.

The selected approach is Docker-based deployment to a private cloud or controlled institutional server. Docker creates a consistent runtime environment and reduces configuration differences between development, testing, and deployment. Because this is an academic healthcare prototype, only synthetic data must be used.

## 2. System Prerequisites

- Windows 10/11, Linux, or macOS
- Python 3.12 or later
- Git
- Docker Desktop or Docker Engine
- At least 2 GB of available memory
- PyTest 9.0.1
- Matplotlib 3.11.2
- Internet access during dependency installation

## 3. Local Installation

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/Taghreed-Almirabi/Integrated-EHR-Access-Control-Framework.git
cd Integrated-EHR-Access-Control-Framework
```

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m ensurepip --upgrade
python -m pip install -r requirements.txt
```

Validate and run the system:

```powershell
python -m pytest -q
python system_demo.py
python performance_evaluation.py
```

## 4. Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| EHR_ENVIRONMENT | Identifies the deployment environment | development |
| EHR_AUDIT_DB_PATH | Defines the audit database location | data/ehr_audit.db |
| EHR_LOG_LEVEL | Controls the planned logging detail | INFO |
| EHR_AUDIT_SECRET | Protects audit-event integrity | Secure external secret |
| EHR_USE_SYNTHETIC_DATA | Prevents the use of real patient information | true |

The `.env.example` file documents the required settings. Real secrets must never be committed to Git. In production, secrets should be stored in a managed secret vault and supplied securely during deployment.

## 5. Docker Build and Execution

Create a local environment file from the provided template:

```powershell
Copy-Item .env.example .env
```

Replace the example secret locally, then build the container image:

```powershell
docker build -t integrated-ehr-access-control:1.0 .
```

Run the container with persistent audit-data storage:

```powershell
docker run --rm --env-file .env -v "${PWD}/data:/app/data" integrated-ehr-access-control:1.0
```

## 6. Configuration Management

Configuration management improves reliability by separating environment-specific values from the program code, fixing dependency versions, and using the same Docker image across test and deployment environments. The `requirements.txt`, `.env.example`, `Dockerfile`, and `.dockerignore` files provide a documented and reproducible configuration baseline.

Before any production use, SQLite should be replaced with an encrypted managed database, transport security should be enforced, access should be restricted through private networking, and audit logs should be backed up and monitored. No real electronic health record or personally identifiable information is included in this academic prototype.