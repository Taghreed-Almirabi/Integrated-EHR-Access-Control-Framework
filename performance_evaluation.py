from __future__ import annotations

import csv
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
        "mfa_verified": True,
    }

    values.update(overrides)
    return AccessRequest(**values)


def measure_decision_accuracy() -> float:
    """Compare system decisions with predefined expected decisions."""
    engine = AccessControlEngine()

    validation_cases = [
        (
            "Authorized physician",
            make_request(user_id="DR-001"),
            AccessDecision.PERMIT,
        ),
        (
            "Authorized pharmacist",
            make_request(
                user_id="PH-001",
                role=UserRole.PHARMACIST,
                action=AccessAction.DISPENSE_MEDICATION,
                department="Pharmacy",
            ),
            AccessDecision.PERMIT,
        ),
        (
            "Unauthenticated nurse",
            make_request(
                user_id="NURSE-001",
                role=UserRole.NURSE,
                action=AccessAction.ADMINISTER_MEDICATION,
                authenticated=False,
            ),
            AccessDecision.DENY,
        ),
        (
            "Emergency break-glass",
            make_request(
                user_id="NURSE-ER-001",
                role=UserRole.NURSE,
                assigned_to_patient=False,
                emergency=True,
                emergency_justification=(
                    "Immediate access is required for emergency care."
                ),
            ),
            AccessDecision.BREAK_GLASS_PERMIT,
        ),
    ]

    correct_decisions = 0

    print("\nDECISION VALIDATION")
    print("-" * 72)

    for name, request, expected_decision in validation_cases:
        result = engine.evaluate(request)
        correct = result.decision == expected_decision
        correct_decisions += int(correct)

        print(
            f"{name:<28} "
            f"Expected: {expected_decision.value:<20} "
            f"Actual: {result.decision.value:<20} "
            f"{'PASS' if correct else 'FAIL'}"
        )

    return (
        correct_decisions / len(validation_cases)
    ) * 100


def measure_integrated_performance() -> tuple[float, float, float]:
    """Measure latency, throughput, and peak memory usage."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = (
            Path(temporary_directory) / "performance_audit.db"
        )
        repository = AuditRepository(database_path)
        service = EHRAccessService(repository=repository)
        request = make_request(user_id="DR-PERFORMANCE")

        for _ in range(10):
            service.process_request(request)

        tracemalloc.start()
        start_time = time.perf_counter()

        for _ in range(TOTAL_PERFORMANCE_REQUESTS):
            service.process_request(request)

        elapsed_time = time.perf_counter() - start_time
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    average_latency_ms = (
        elapsed_time / TOTAL_PERFORMANCE_REQUESTS
    ) * 1000
    throughput = TOTAL_PERFORMANCE_REQUESTS / elapsed_time
    peak_memory_mb = peak_memory / (1024 * 1024)

    return average_latency_ms, throughput, peak_memory_mb


def assess_interface_clarity() -> tuple[dict[str, int], float]:
    """Record a structured heuristic review using a five-point scale."""
    usability_scores = {
        "Decision labels": 5,
        "Reason explanations": 5,
        "Input consistency": 4,
        "Audit traceability": 5,
        "Ease of learning": 4,
    }

    average_score = (
        sum(usability_scores.values())
        / len(usability_scores)
    )

    return usability_scores, average_score


def save_results_table(
    accuracy: float,
    latency: float,
    throughput: float,
    peak_memory: float,
    usability: float,
) -> Path:
    """Save quantitative and qualitative findings as a CSV table."""
    RESULTS_DIRECTORY.mkdir(exist_ok=True)
    table_path = RESULTS_DIRECTORY / "evaluation_results.csv"

    rows = [
        ["Decision accuracy", f"{accuracy:.2f}%", "Quantitative"],
        ["Average latency", f"{latency:.3f} ms", "Quantitative"],
        [
            "Throughput",
            f"{throughput:.2f} requests/second",
            "Quantitative",
        ],
        ["Peak memory", f"{peak_memory:.3f} MB", "Quantitative"],
        ["Interface clarity", f"{usability:.2f}/5", "Qualitative"],
    ]

    with table_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Metric", "Result", "Metric Type"])
        writer.writerows(rows)

    print("\nSTRUCTURED RESULTS TABLE")
    print("-" * 72)
    print(f"{'Metric':<24}{'Result':<28}{'Type'}")
    print("-" * 72)

    for metric, result, metric_type in rows:
        print(f"{metric:<24}{result:<28}{metric_type}")

    return table_path


def create_results_chart(
    accuracy: float,
    latency: float,
    throughput: float,
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

    axes[0, 0].bar(
        ["Decision Accuracy"],
        [accuracy],
        color="#2E86AB",
    )
    axes[0, 0].set_ylim(0, 100)
    axes[0, 0].set_ylabel("Percentage (%)")
    axes[0, 0].set_title("Policy Decision Accuracy")
    axes[0, 0].text(
        0,
        accuracy - 5,
        f"{accuracy:.2f}%",
        ha="center",
    )

    axes[0, 1].bar(
        ["Average Latency"],
        [latency],
        color="#F18F01",
    )
    axes[0, 1].set_ylim(0, max(latency * 1.4, 1))
    axes[0, 1].set_ylabel("Milliseconds (ms)")
    axes[0, 1].set_title("Average Request Latency")
    axes[0, 1].text(
        0,
        latency * 1.05,
        f"{latency:.3f} ms",
        ha="center",
    )

    axes[1, 0].bar(
        ["Throughput"],
        [throughput],
        color="#3D9970",
    )
    axes[1, 0].set_ylim(0, max(throughput * 1.3, 1))
    axes[1, 0].set_ylabel("Requests per second")
    axes[1, 0].set_title("Integrated System Throughput")
    axes[1, 0].text(
        0,
        throughput * 1.04,
        f"{throughput:.2f}",
        ha="center",
    )

    criteria = list(usability_scores.keys())
    scores = list(usability_scores.values())

    axes[1, 1].barh(
        criteria,
        scores,
        color="#7B2CBF",
    )
    axes[1, 1].set_xlim(0, 5)
    axes[1, 1].set_xlabel("Heuristic score (1–5)")
    axes[1, 1].set_title("Interface Clarity Assessment")

    figure.tight_layout(rect=(0, 0, 1, 0.95))
    figure.savefig(
        chart_path,
        dpi=200,
        bbox_inches="tight",
    )
    plt.close(figure)

    return chart_path


def main() -> None:
    """Run the complete system evaluation."""
    print("=" * 72)
    print("INTEGRATED EHR ACCESS CONTROL SYSTEM EVALUATION")
    print("Synthetic data only")
    print("=" * 72)

    accuracy = measure_decision_accuracy()
    latency, throughput, peak_memory = (
        measure_integrated_performance()
    )
    usability_scores, usability_average = (
        assess_interface_clarity()
    )

    print("\nQUALITATIVE CLARITY ASSESSMENT")
    print("-" * 72)

    for criterion, score in usability_scores.items():
        print(f"{criterion:<28}: {score}/5")

    print(f"{'Average clarity score':<28}: {usability_average:.2f}/5")

    table_path = save_results_table(
        accuracy,
        latency,
        throughput,
        peak_memory,
        usability_average,
    )
    chart_path = create_results_chart(
        accuracy,
        latency,
        throughput,
        usability_scores,
    )

    print("\nEVALUATION FILES CREATED")
    print("-" * 72)
    print(f"Results table: {table_path.resolve()}")
    print(f"Results chart: {chart_path.resolve()}")


if __name__ == "__main__":
    main()