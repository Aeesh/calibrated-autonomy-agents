from calibration_data import X_SITE_KNOWLEDGE, A_SITE_MN_U_EV, X_SITE_CATIONS
from qe_input_writer import new_candidate_scf
from qe_job_runner import attempt_run


class NewCandidateAgent:
    """Assesses a material not in the calibration set: no known outcome
    to check against. Decides using X-site cation knowledge extracted
    from CalibrationAgent's four materials (which X-site cations needed
    a Hubbard U correction, which didn't, and why (d-shell filling)),
    and cross-checks the same FailurePlaybook the calibration stage
    built, for whichever calibration material it ends up analogising
    to."""

    def __init__(self, playbook=None):
        self.playbook = playbook

    def _playbook_note(self, analog_cation):
        """Was a diagnosed failure ever learned from the calibration
        material that hosts this analog cation? Returns a log line, or
        None if there's no playbook to check or no analog material to
        check it against."""
        if self.playbook is None:
            return None
        analog_material = next(
            (mat for mat, cat in X_SITE_CATIONS.items() if cat == analog_cation), None
        )
        if analog_material is None:
            return None
        has_prior_failure = any(
            entry["learned_from"] == analog_material for entry in self.playbook.entries.values()
        )
        if has_prior_failure:
            return (
                f"Checked the failure playbook: {analog_material} (the analog material) has a "
                "diagnosed failure on record - treating this analogy with extra caution."
            )
        return (
            f"Checked the failure playbook for {analog_material} (the analog material): "
            "no diagnosed failure on record."
        )

    def assess(self, material, x_cation, x_d_shell):
        log = []

        if x_cation in X_SITE_KNOWLEDGE:
            entry = X_SITE_KNOWLEDGE[x_cation]
            log.append(f"{x_cation} is already in the calibration set (U = {entry['U_eV']}).")
            return log, "CALIBRATED", entry["U_eV"]

        # Look for a calibration cation with the same d-shell filling.
        analog = None
        for cation, entry in X_SITE_KNOWLEDGE.items():
            if entry["d_shell"] == x_d_shell:
                analog = (cation, entry)
                break

        if analog is None:
            log.append(
                f"{x_cation} (d{x_d_shell}) has no U parameter and no calibration cation shares its "
                "d-shell filling. No defensible analogy exists."
            )
            log.append("Recommending a linear-response U calculation before any SCF run.")
            return log, "ESCALATE_NO_ANALOG", None

        analog_cation, analog_entry = analog
        log.append(
            f"{x_cation} (d{x_d_shell}) has no reported U, but shares its d-shell filling with "
            f"{analog_cation} (also d{analog_entry['d_shell']})."
        )

        playbook_note = self._playbook_note(analog_cation)
        if playbook_note:
            log.append(playbook_note)

        if analog_entry["U_eV"] is None:
            log.append(
                f"{analog_cation} needed no Hubbard correction (full d-shell, no self-interaction "
                f"error to correct). Predicting the same for {x_cation}: run without U, treat as a "
                "prediction pending confirmation, not a settled result."
            )
            return log, "PREDICT_NO_U_NEEDED", None
        else:
            log.append(f"{analog_cation} used U = {analog_entry['U_eV']:.2f} eV. Proposing that as a starting value for {x_cation}, pending its own linear-response calculation.")
            return log, "PREDICT_U_BY_ANALOGY", analog_entry["U_eV"]

    def run(self, material, x_cation, x_d_shell, output_dir):
        log, status, u_value = self.assess(material, x_cation, x_d_shell)

        if status == "ESCALATE_NO_ANALOG":
            return log, status, None

        config_label = "AFM_first_attempt"
        input_text = new_candidate_scf(material, x_cation, u_value, config_label)
        input_path = f"{output_dir}/{material}_{config_label}.in"
        with open(input_path, "w") as f:
            f.write(input_text)
        log.append(f"Wrote {input_path}.")

        ran, message = attempt_run(input_path, input_path.replace(".in", ".out"))
        log.append(f"Execution attempt: {message}")

        return log, status, input_path
