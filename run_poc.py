import os
from datetime import datetime, timezone
from calibration_data import CALIBRATION_MATERIALS, CALIBRATION_ORDER, NEW_CANDIDATES
from calibration_agent import FailurePlaybook, CalibrationAgent
from new_candidate_agent import NewCandidateAgent
from scf_log_parser import parse_first_scf_block
from live_convergence_monitor import SCFLiveMonitorAgent

RAW_SCF_FILE = os.path.join(os.path.dirname(__file__), "data", "scf.MnCoWO4_AFM.out")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated_inputs")
RUNS_DIR = os.path.join(os.path.dirname(__file__), "runs")


def run_live_monitor(lines):
    lines.append("=" * 70)
    lines.append("STAGE 1: CONVERGENCE MONITOR")
    lines.append("=" * 70)
    if not os.path.exists(RAW_SCF_FILE):
        lines.append(f"  {RAW_SCF_FILE} not found.")
        return
    trace, qe_reported = parse_first_scf_block(RAW_SCF_FILE)
    lines.append(f"  Loaded {len(trace)} iterations from {os.path.basename(RAW_SCF_FILE)}")
    agent = SCFLiveMonitorAgent()
    decisions, final = agent.run(trace)
    for iteration, action, reason in decisions:
        if action != "CONTINUE" or iteration in (1, 15, 20, 22):
            lines.append(f"  iter {iteration:>3}: {action:<9} {reason}")
    lines.append(f"  agent: {final}  |  QE reported convergence at iteration {qe_reported}")


def run_calibration(lines):
    lines.append("\n" + "=" * 70)
    lines.append("STAGE 2: CALIBRATION")
    lines.append("=" * 70)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Calibration builds the playbook before the new materials are assessed.
    playbook = FailurePlaybook()
    agent = CalibrationAgent(playbook)

    for name in CALIBRATION_ORDER:
        record = CALIBRATION_MATERIALS[name]
        lines.append(f"\n--- {name}  [{record['source']}] ---")
        log, status, artifacts = agent.investigate(name, record)
        for line in log:
            lines.append(f"  {line}")
        lines.append(f"  => {status}")
        for filename, content in artifacts:
            with open(os.path.join(OUTPUT_DIR, filename), "w") as f:
                f.write(content)

    lines.append("\n  playbook after calibration:")
    if not playbook.entries:
        lines.append("    (empty)")
    for sig, entry in playbook.entries.items():
        lines.append(f"    learned from {entry['learned_from']}: {entry['fix']}")
    return playbook


def run_new_candidates(lines, playbook):
    lines.append("\n" + "=" * 70)
    lines.append("STAGE 3: NEW CANDIDATES")
    lines.append("=" * 70)
    agent = NewCandidateAgent(playbook)
    for name, spec in NEW_CANDIDATES.items():
        lines.append(f"\n--- {name}  [{spec['source']}] ---")
        log, status, artifact = agent.run(name, spec["x_cation"], spec["x_d_shell"], OUTPUT_DIR)
        for line in log:
            lines.append(f"  {line}")
        lines.append(f"  => {status}")


def main():
    lines = []
    run_live_monitor(lines)
    playbook = run_calibration(lines)
    run_new_candidates(lines, playbook)
    lines.append(
        "\nThe agent generates and attempts to run each QE input file it decides on. "
        "This environment has no pw.x and no cluster access, so execution fails here; "
        "the input file is left ready for a human or job scheduler to submit."
    )
    output = "\n".join(lines)
    print(output)

    os.makedirs(RUNS_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = os.path.join(RUNS_DIR, f"run_{timestamp}.log")
    with open(log_path, "w") as f:
        f.write(output)
    print(f"\n(saved to {log_path})")


if __name__ == "__main__":
    main()
