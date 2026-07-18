from calibration_data import NOISE_FLOOR, NOISE_FLOOR_UNIT, DEGENERATE_CUTOFF, RECHECK_COST_MIN
from qe_input_writer import known_fix_rerun, recheck_denser_kmesh


class FailurePlaybook:
    def __init__(self):
        self.entries = {}

    @staticmethod
    def _signature(failure_signals):
        return tuple(sorted(failure_signals.items()))

    def lookup(self, failure_signals):
        return self.entries.get(self._signature(failure_signals))

    def learn(self, failure_signals, fix, learned_from):
        self.entries[self._signature(failure_signals)] = {"fix": fix, "learned_from": learned_from}


class CalibrationAgent:
    """Per-material check against the four already-run materials. Builds
    the failure playbook and exercises the noise-floor/recheck logic that
    NewCandidateAgent reuses."""

    def __init__(self, playbook):
        self.playbook = playbook

    def investigate(self, case_name, record):
        log = []
        a, b = record["candidate_a"], record["candidate_b"]
        artifacts = []

        if not a["converged"]:
            match = self.playbook.lookup(a["failure_signals"])
            if match:
                log.append(f"{a['label']} failed. Matches signature learned from {match['learned_from']}.")
                fix_text = match["fix"]
                status = "ESCALATE_WITH_KNOWN_FIX"
            else:
                fix_text = a.get("known_fix")
                if fix_text:
                    self.playbook.learn(a["failure_signals"], fix_text, case_name)
                    log.append(f"{a['label']} failed. New signature, diagnosing from scratch.")
                else:
                    log.append(f"{a['label']} failed. New signature, no diagnosis available.")
                    fix_text = None
                status = "ESCALATE_NEW_DIAGNOSIS"

            if fix_text:
                log.append(f"Fix: {fix_text}")
                input_text = known_fix_rerun(case_name, record["cations"])
                artifacts.append((f"{case_name}_AFM_recheck.in", input_text))

            log.append(f"No {a['label']}/{b['label']} comparison possible: {a['label']} never converged.")
            return log, status, artifacts

        delta = record["delta"]
        source_note = (
            "computed from raw parsed energies"
            if record.get("delta_source") == "computed_from_raw_energies"
            else "from prior report, no raw-energy computation available"
        )
        log.append(f"Delta {delta:+.2f} {NOISE_FLOOR_UNIT} ({source_note}).")

        if abs(delta) < DEGENERATE_CUTOFF:
            log.append(f"Gap {delta:+.2f} {NOISE_FLOOR_UNIT} is at the noise floor's own resolution limit.")
            log.append("No realistic recheck would separate this; reporting as genuinely degenerate.")
            return log, "ESCALATE_DEGENERATE", artifacts

        if abs(delta) < NOISE_FLOOR:
            log.append(
                f"Gap {delta:+.2f} {NOISE_FLOOR_UNIT} is inside the {NOISE_FLOOR:.1f} {NOISE_FLOOR_UNIT} "
                f"noise floor but not near zero - a denser k-mesh recheck (~{RECHECK_COST_MIN:.0f} min) "
                "could plausibly resolve it."
            )
            x_cation = [c for c in record["cations"] if c not in ("Mn", "W")][0]
            input_text = recheck_denser_kmesh(case_name, record["cations"], x_cation, None)
            artifacts.append((f"{case_name}_recheck_densekmesh.in", input_text))
            return log, "ESCALATE_VERIFY_WORTHWHILE", artifacts

        winner = a["label"] if delta < 0 else b["label"]
        log.append(f"{winner} favored by {abs(delta):.2f} {NOISE_FLOOR_UNIT}, above the noise floor.")
        return log, "CONCLUDE", artifacts
