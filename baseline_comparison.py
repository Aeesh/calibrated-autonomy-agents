import os
from datetime import datetime, timezone
from calibration_data import CALIBRATION_MATERIALS, CALIBRATION_ORDER, NOISE_FLOOR, DEGENERATE_CUTOFF
from calibration_agent import FailurePlaybook, CalibrationAgent

RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")


def naive_run(record):
    """No playbook, no recheck-vs-degenerate distinction: converged
    result is fact, any within-noise gap is a flat escalate."""
    a = record["candidate_a"]
    if not a["converged"]:
        return "ESCALATE_NO_DIAGNOSIS"
    delta = record["delta"]
    if abs(delta) < NOISE_FLOOR:
        return "ESCALATE_FLAT"
    return "CONCLUDE"


def main():
    lines = []
    playbook = FailurePlaybook()
    agent = CalibrationAgent(playbook)

    lines.append("=== Agent (playbook + recheck-vs-degenerate) ===")
    agent_results = {}
    for name in CALIBRATION_ORDER:
        _, status, _ = agent.investigate(name, CALIBRATION_MATERIALS[name])
        agent_results[name] = status
        lines.append(f"  {name}: {status}")

    lines.append("\n=== Naive baseline (no playbook, no recheck distinction) ===")
    baseline_results = {name: naive_run(CALIBRATION_MATERIALS[name]) for name in CALIBRATION_ORDER}
    for name, status in baseline_results.items():
        lines.append(f"  {name}: {status}")

    lines.append("\n=== Where they differ ===")
    for name in CALIBRATION_ORDER:
        if agent_results[name] != baseline_results[name]:
            lines.append(f"  {name}: agent={agent_results[name]} vs baseline={baseline_results[name]}")

    recheck_flagged = [n for n in CALIBRATION_ORDER if agent_results[n] == "ESCALATE_VERIFY_WORTHWHILE"]
    degenerate_flagged = [n for n in CALIBRATION_ORDER if agent_results[n] == "ESCALATE_DEGENERATE"]
    lines.append(f"\nAgent separates {len(recheck_flagged)} recheck-worthwhile case(s) {recheck_flagged}")
    lines.append(f"from {len(degenerate_flagged)} genuinely-degenerate case(s) {degenerate_flagged}.")
    lines.append("The naive baseline reports both as the same flat ESCALATE_FLAT, losing that distinction.")

    output = "\n".join(lines)
    print(output)

    os.makedirs(RUNS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = os.path.join(RUNS_DIR, f"baseline_comparison_{timestamp}.log")
    with open(log_path, "w") as f:
        f.write(output)
    print(f"\n(saved to {log_path})")


if __name__ == "__main__":
    main()
