"""System evaluation for the Integrated EHR Access-Control Framework.

Final-submission version. Compared with the Unit 6 script it adds:
- a 36-case labeled decision benchmark (six cases per role),
- per-request latency recording with median, p95 and p99 percentiles,
- capture of the benchmark environment (OS, CPU, RAM, Python),
- the same CSV and chart outputs, extended with the new measures.

Synthetic data only. No real users, patients or hospital systems.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from src.access_control_engine import (
    AccessAction,
    AccessControlEngine,
    AccessDecision,
    AccessRequest,
    UserRole,
)
from src.audit_repository import AuditRepository
from src.ehr_access_service import EHRAccessService


RESULTS_DIRECTORY = Path("results")
WARM_UP_REQUESTS = 10
TOTAL_PERFORMANCE_REQUESTS = 300


def make_request(**overrides) -> AccessRequest:
    """Create a valid synthetic request for system evaluation."""
    values = {
        "user_id": "DR-EVALUATION",
        "role": UserRole.PHYSICIAN,
        "action": AccessAction.VIEW_PATIENT_RECORD,
        "patient_id": "PATIENT-EVALUATION",
        "department": "Emergency",
        "location": "Evaluation Hospital",
        "authenticated": True,
        "account_active": True,
        "on_duty": True,
        "assigned_to_patient": True,
        "on_hospital_network": True,
        "managed_device": True,
        "mfa_verified": False,
    }

    values.update(overrides)
    return AccessRequest(**values)


JUSTIFICATION = "Unresponsive patient in the emergency department."


def build_validation_cases() -> list[tuple[str, AccessRequest, AccessDecision]]:
    """Return the 36 labeled validation cases (six per role)."""
    permit = AccessDecision.PERMIT
    deny = AccessDecision.DENY
    mfa = AccessDecision.STEP_UP_MFA
    glass = AccessDecision.BREAK_GLASS_PERMIT

    physician = UserRole.PHYSICIAN
    nurse = UserRole.NURSE
    pharmacist = UserRole.PHARMACIST
    lab = UserRole.LAB_TECHNICIAN
    him = UserRole.HEALTH_INFORMATION_MANAGER
    admin = UserRole.IT_SYSTEMS_ADMINISTRATOR

    return [
        # Physician
        ("P1 Assigned physician views record", make_request(user_id="DR-001"), permit),
        ("P2 Assigned physician prescribes", make_request(user_id="DR-002", action=AccessAction.PRESCRIBE_MEDICATION), permit),
        ("P3 Physician not assigned to patient", make_request(user_id="DR-003", assigned_to_patient=False), deny),
        ("P4 Physician outside duty period", make_request(user_id="DR-004", on_duty=False), deny),
        ("P5 Physician off-network without MFA", make_request(user_id="DR-005", on_hospital_network=False), mfa),
        ("P6 Physician emergency break-glass", make_request(user_id="DR-006", assigned_to_patient=False, emergency=True, emergency_justification=JUSTIFICATION), glass),
        # Nurse
        ("N1 Assigned nurse administers medication", make_request(user_id="RN-001", role=nurse, action=AccessAction.ADMINISTER_MEDICATION), permit),
        ("N2 Nurse attempts to prescribe", make_request(user_id="RN-002", role=nurse, action=AccessAction.PRESCRIBE_MEDICATION), deny),
        ("N3 Unauthenticated nurse", make_request(user_id="RN-003", role=nurse, authenticated=False), deny),
        ("N4 Nurse on unmanaged device without MFA", make_request(user_id="RN-004", role=nurse, managed_device=False), mfa),
        ("N5 Nurse emergency without justification", make_request(user_id="RN-005", role=nurse, emergency=True, emergency_justification=""), deny),
        ("N6 Nurse emergency for non-clinical action", make_request(user_id="RN-006", role=nurse, action=AccessAction.REVIEW_AUDIT_LOGS, emergency=True, emergency_justification=JUSTIFICATION), deny),
        # Pharmacist
        ("PH1 Pharmacist dispenses medication", make_request(user_id="PH-001", role=pharmacist, action=AccessAction.DISPENSE_MEDICATION), permit),
        ("PH2 Pharmacist views record", make_request(user_id="PH-002", role=pharmacist), permit),
        ("PH3 Pharmacist attempts to administer", make_request(user_id="PH-003", role=pharmacist, action=AccessAction.ADMINISTER_MEDICATION), deny),
        ("PH4 Pharmacist dispenses without patient", make_request(user_id="PH-004", role=pharmacist, action=AccessAction.DISPENSE_MEDICATION, patient_id=None), deny),
        ("PH5 Pharmacist with inactive account", make_request(user_id="PH-005", role=pharmacist, account_active=False), deny),
        ("PH6 Pharmacist attempts break-glass", make_request(user_id="PH-006", role=pharmacist, emergency=True, emergency_justification=JUSTIFICATION), deny),
        # Laboratory technician
        ("L1 Technician records lab result", make_request(user_id="LAB-001", role=lab, action=AccessAction.RECORD_LAB_RESULT), permit),
        ("L2 Technician views record", make_request(user_id="LAB-002", role=lab), permit),
        ("L3 Technician edits clinical notes", make_request(user_id="LAB-003", role=lab, action=AccessAction.UPDATE_CLINICAL_NOTES), deny),
        ("L4 Technician outside duty period", make_request(user_id="LAB-004", role=lab, action=AccessAction.RECORD_LAB_RESULT, on_duty=False), deny),
        ("L5 Technician off-network without MFA", make_request(user_id="LAB-005", role=lab, on_hospital_network=False), mfa),
        ("L6 Technician off-network with verified MFA", make_request(user_id="LAB-006", role=lab, on_hospital_network=False, mfa_verified=True), permit),
        # Health information manager
        ("H1 HIM views record", make_request(user_id="HIM-001", role=him), permit),
        ("H2 HIM export without MFA", make_request(user_id="HIM-002", role=him, action=AccessAction.EXPORT_PATIENT_RECORD), mfa),
        ("H3 HIM export with verified MFA", make_request(user_id="HIM-003", role=him, action=AccessAction.EXPORT_PATIENT_RECORD, mfa_verified=True), permit),
        ("H4 HIM reviews audit logs", make_request(user_id="HIM-004", role=him, action=AccessAction.REVIEW_AUDIT_LOGS, patient_id=None), permit),
        ("H5 HIM with blank user identifier", make_request(user_id="   ", role=him), deny),
        ("H6 HIM attempts to prescribe", make_request(user_id="HIM-006", role=him, action=AccessAction.PRESCRIBE_MEDICATION), deny),
        # IT systems administrator
        ("A1 Admin manages accounts without MFA", make_request(user_id="IT-001", role=admin, action=AccessAction.MANAGE_USER_ACCOUNTS, patient_id=None), mfa),
        ("A2 Admin manages accounts with verified MFA", make_request(user_id="IT-002", role=admin, action=AccessAction.MANAGE_USER_ACCOUNTS, patient_id=None, mfa_verified=True), permit),
        ("A3 Admin reviews audit logs", make_request(user_id="IT-003", role=admin, action=AccessAction.REVIEW_AUDIT_LOGS, patient_id=None), permit),
        ("A4 Admin attempts to view clinical record", make_request(user_id="IT-004", role=admin), deny),
        ("A5 Admin attempts break-glass", make_request(user_id="IT-005", role=admin, emergency=True, emergency_justification=JUSTIFICATION), deny),
        ("A6 Admin reviews logs from unmanaged device", make_request(user_id="IT-006", role=admin, action=AccessAction.REVIEW_AUDIT_LOGS, patient_id=None, managed_device=False), mfa),
    ]


def measure_decision_accuracy() -> tuple[float, int, int, int]:
    """Compare engine decisions with the labeled expected decisions.

    Returns accuracy (%), number of cases, number correct and the number of
    false permits (a PERMIT or BREAK_GLASS_PERMIT where DENY or MFA was expected).
    """
    engine = AccessControlEngine()
    cases = build_validation_cases()
    correct = 0
    false_permits = 0

    print("\nDECISION VALIDATION (36 labeled cases)")
    print("-" * 88)

    for name, request, expected in cases:
        result = engine.evaluate(request)
        is_correct = result.decision == expected
        correct += int(is_correct)
        if not is_correct and result.decision in (
            AccessDecision.PERMIT,
            AccessDecision.BREAK_GLASS_PERMIT,
        ):
            false_permits += 1
        print(
            f"{name:<46} Expected: {expected.value:<19} "
            f"Actual: {result.decision.value:<19} {'PASS' if is_correct else 'FAIL'}"
        )

    accuracy = correct / len(cases) * 100
    print("-" * 88)
    print(f"Correct decisions: {correct}/{len(cases)}  False permits: {false_permits}")
    return accuracy, len(cases), correct, false_permits


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile on an ascending list."""
    if not sorted_values:
        return 0.0
    rank = max(1, int(round(fraction * len(sorted_values))))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def measure_integrated_performance() -> dict[str, float]:
    """Measure per-request latency statistics, throughput and peak memory."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "performance_audit.db"
        repository = AuditRepository(database_path)
        service = EHRAccessService(repository=repository)
        request = make_request(user_id="DR-PERFORMANCE", mfa_verified=True)

        for _ in range(WARM_UP_REQUESTS):
            service.process_request(request)

        latencies_ms: list[float] = []
        tracemalloc.start()
        block_start = time.perf_counter()

        for _ in range(TOTAL_PERFORMANCE_REQUESTS):
            started = time.perf_counter()
            service.process_request(request)
            latencies_ms.append((time.perf_counter() - started) * 1000)

        elapsed = time.perf_counter() - block_start
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    ordered = sorted(latencies_ms)
    return {
        "mean_ms": statistics.fmean(latencies_ms),
        "median_ms": statistics.median(latencies_ms),
        "p95_ms": percentile(ordered, 0.95),
        "p99_ms": percentile(ordered, 0.99),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "throughput_rps": TOTAL_PERFORMANCE_REQUESTS / elapsed,
        "peak_memory_mb": peak_memory / (1024 * 1024),
    }


def total_memory_gb() -> float | None:
    """Best-effort total physical memory in GB (Windows, Linux, macOS)."""
    try:
        if sys.platform.startswith("win"):
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / (1024 ** 3), 1)
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024 ** 3), 1)
    except Exception:  # noqa: BLE001 - best effort only
        return None


def describe_environment() -> dict[str, str]:
    """Capture the benchmark environment for reproducibility."""
    memory = total_memory_gb()
    return {
        "Operating system": platform.platform(),
        "Processor": platform.processor() or platform.machine(),
        "Logical CPUs": str(os.cpu_count()),
        "Physical memory": f"{memory} GB" if memory else "unknown",
        "Python": platform.python_version(),
        "Warm-up requests": str(WARM_UP_REQUESTS),
        "Timed requests": str(TOTAL_PERFORMANCE_REQUESTS),
        "Timer": "time.perf_counter per request; tracemalloc peak over the timed block",
    }


def assess_interface_clarity() -> tuple[dict[str, int], float]:
    """Record the structured heuristic review (five-point scale)."""
    usability_scores = {
        "Decision labels": 5,
        "Reason explanations": 5,
        "Input consistency": 4,
        "Audit traceability": 5,
        "Ease of learning": 4,
    }
    return usability_scores, sum(usability_scores.values()) / len(usability_scores)


def save_results_table(
    accuracy: float,
    cases: int,
    correct: int,
    false_permits: int,
    perf: dict[str, float],
    usability: float,
    environment: dict[str, str],
) -> Path:
    """Save quantitative and qualitative findings as a CSV table."""
    RESULTS_DIRECTORY.mkdir(exist_ok=True)
    table_path = RESULTS_DIRECTORY / "evaluation_results.csv"

    rows = [
        ["Decision accuracy", f"{accuracy:.2f}% ({correct}/{cases})", "Quantitative"],
        ["False permits", str(false_permits), "Quantitative"],
        ["Mean latency", f"{perf['mean_ms']:.3f} ms", "Quantitative"],
        ["Median latency", f"{perf['median_ms']:.3f} ms", "Quantitative"],
        ["p95 latency", f"{perf['p95_ms']:.3f} ms", "Quantitative"],
        ["p99 latency", f"{perf['p99_ms']:.3f} ms", "Quantitative"],
        ["Minimum latency", f"{perf['min_ms']:.3f} ms", "Quantitative"],
        ["Maximum latency", f"{perf['max_ms']:.3f} ms", "Quantitative"],
        ["Throughput", f"{perf['throughput_rps']:.2f} requests/second", "Quantitative"],
        ["Peak memory", f"{perf['peak_memory_mb']:.3f} MB", "Quantitative"],
        ["Interface clarity", f"{usability:.2f}/5", "Qualitative"],
    ]
    for key, value in environment.items():
        rows.append([key, value, "Environment"])

    with table_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Metric", "Result", "Metric Type"])
        writer.writerows(rows)

    environment_path = RESULTS_DIRECTORY / "evaluation_environment.json"
    environment_path.write_text(json.dumps(environment, indent=2), encoding="utf-8")

    print("\nSTRUCTURED RESULTS TABLE")
    print("-" * 88)
    print(f"{'Metric':<24}{'Result':<44}{'Type'}")
    print("-" * 88)
    for metric, result, metric_type in rows:
        print(f"{metric:<24}{result:<44}{metric_type}")

    return table_path


def create_results_chart(
    accuracy: float,
    perf: dict[str, float],
    usability_scores: dict[str, int],
) -> Path:
    """Create a visual summary of the evaluation findings."""
    RESULTS_DIRECTORY.mkdir(exist_ok=True)
    chart_path = RESULTS_DIRECTORY / "system_evaluation_chart.png"

    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    figure.suptitle(
        "Integrated EHR Access Control System Evaluation",
        fontsize=15,
        fontweight="bold",
    )

    axes[0, 0].bar(["Decision Accuracy"], [accuracy], color="#2E86AB")
    axes[0, 0].set_ylim(0, 100)
    axes[0, 0].set_ylabel("Percentage (%)")
    axes[0, 0].set_title("Policy Decision Accuracy (36 labeled cases)")
    axes[0, 0].text(0, accuracy - 5, f"{accuracy:.2f}%", ha="center")

    labels = ["Mean", "Median", "p95", "p99"]
    values = [perf["mean_ms"], perf["median_ms"], perf["p95_ms"], perf["p99_ms"]]
    bars = axes[0, 1].bar(labels, values, color="#F18F01")
    axes[0, 1].set_ylim(0, max(values) * 1.35)
    axes[0, 1].set_ylabel("Milliseconds (ms)")
    axes[0, 1].set_title("Request Latency Distribution")
    for bar, value in zip(bars, values):
        axes[0, 1].text(bar.get_x() + bar.get_width() / 2, value * 1.04, f"{value:.2f}", ha="center")

    axes[1, 0].bar(["Throughput"], [perf["throughput_rps"]], color="#3D9970")
    axes[1, 0].set_ylim(0, max(perf["throughput_rps"] * 1.3, 1))
    axes[1, 0].set_ylabel("Requests per second")
    axes[1, 0].set_title("Integrated System Throughput")
    axes[1, 0].text(0, perf["throughput_rps"] * 1.04, f"{perf['throughput_rps']:.2f}", ha="center")

    axes[1, 1].barh(list(usability_scores.keys()), list(usability_scores.values()), color="#7B2CBF")
    axes[1, 1].set_xlim(0, 5)
    axes[1, 1].set_xlabel("Heuristic score (1-5)")
    axes[1, 1].set_title("Interface Clarity Assessment")

    figure.tight_layout(rect=(0, 0, 1, 0.95))
    figure.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close(figure)
    return chart_path


def main() -> None:
    """Run the complete system evaluation."""
    print("=" * 88)
    print("INTEGRATED EHR ACCESS CONTROL SYSTEM EVALUATION (final submission)")
    print("Synthetic data only")
    print("=" * 88)

    accuracy, cases, correct, false_permits = measure_decision_accuracy()
    perf = measure_integrated_performance()
    usability_scores, usability_average = assess_interface_clarity()
    environment = describe_environment()

    print("\nBENCHMARK ENVIRONMENT")
    print("-" * 88)
    for key, value in environment.items():
        print(f"{key:<24}: {value}")

    print("\nQUALITATIVE CLARITY ASSESSMENT")
    print("-" * 88)
    for criterion, score in usability_scores.items():
        print(f"{criterion:<28}: {score}/5")
    print(f"{'Average clarity score':<28}: {usability_average:.2f}/5")

    table_path = save_results_table(
        accuracy, cases, correct, false_permits, perf, usability_average, environment
    )
    chart_path = create_results_chart(accuracy, perf, usability_scores)

    print("\nEVALUATION FILES CREATED")
    print("-" * 88)
    print(f"Results table: {table_path.resolve()}")
    print(f"Environment:   {(RESULTS_DIRECTORY / 'evaluation_environment.json').resolve()}")
    print(f"Results chart: {chart_path.resolve()}")


if __name__ == "__main__":
    main()
