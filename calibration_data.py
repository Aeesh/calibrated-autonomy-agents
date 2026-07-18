import os
import re
from qe_output_parser import parse_scf_output

NOISE_FLOOR = 2.0
NOISE_FLOOR_UNIT = "meV/atom"
DEGENERATE_CUTOFF = 0.3
RECHECK_COST_MIN = 55.0
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 1 Ry = 13.605693009 eV = 13605.693009 meV (CODATA).
RY_TO_MEV = 13605.693009
# Atoms per formula unit, from the report's space group / atom count:
# 2 A-site (Mn), 2 X-site, 2 W, 6 O.
NAT_ATOMS = 12

# X-site information extracted from the calibration materials in the report.
# These values are only used when no matching raw SCF output is available.
X_SITE_KNOWLEDGE = {
    "Fe": {"d_shell": 5, "U_eV": 5.30},
    "Co": {"d_shell": 7, "U_eV": 7.84},
    "Ni": {"d_shell": 8, "U_eV": 6.45},
    "Zn": {"d_shell": 10, "U_eV": None},
}
A_SITE_MN_U_EV = 4.65

REPORT_DELTAS_MEV_PER_ATOM = {"MnCoWO4": -1.1, "MnNiWO4": -0.9, "MnZnWO4": 0.0, "MnFeWO4": None}
REPORT_VALUES_RY = {
    ("MnCoWO4", "AFM"): -1090.463, ("MnCoWO4", "FM"): -1090.463,
    ("MnNiWO4", "AFM"): -1120.124, ("MnNiWO4", "FM"): -1120.123,
    ("MnZnWO4", "AFM"): -1202.892, ("MnZnWO4", "FM"): -1202.892,
    ("MnFeWO4", "FM"): -1035.285,
}
MNFEWO4_AFM_FAILURE_SIGNALS = {
    "charge_density_negative": True,
    "oscillating_hubbard_energy": True,
    "partially_filled_d_shell": True,
}
MNFEWO4_AFM_KNOWN_FIX = (
    "reduce mixing_beta from 0.7 to 0.3, switch to local-TF mixing, "
    "set starting_magnetization(Fe) = -0.50"
)

X_SITE_CATIONS = {"MnCoWO4": "Co", "MnNiWO4": "Ni", "MnZnWO4": "Zn", "MnFeWO4": "Fe"}
CALIBRATION_ORDER = ["MnCoWO4", "MnNiWO4", "MnZnWO4", "MnFeWO4"]


def _find_raw_file(material, config):
    """Matches scf_<Material>_<AFM|FM>.out or scf.<Material>_<AFM|FM>.out,
    so files can be dropped in with either separator."""
    if not os.path.isdir(DATA_DIR):
        return None
    pattern = re.compile(rf"^scf[._]{re.escape(material)}_{config}\.out$", re.IGNORECASE)
    for filename in os.listdir(DATA_DIR):
        if pattern.match(filename):
            return os.path.join(DATA_DIR, filename)
    return None


def _leg(material, config):
    raw_path = _find_raw_file(material, config)
    if raw_path:
        parsed = parse_scf_output(raw_path)
        return {
            "source": "real_raw_output",
            "converged": parsed["converged"],
            "value": parsed["E_Ry"],
            "wall_seconds": parsed["wall_seconds"],
            "failure_signals": None,
        }

    if material == "MnFeWO4" and config == "AFM":
        return {
            "source": "real_report",
            "converged": False,
            "value": None,
            "failure_signals": MNFEWO4_AFM_FAILURE_SIGNALS,
            "known_fix": MNFEWO4_AFM_KNOWN_FIX,
        }

    return {
        "source": "real_report",
        "converged": True,
        "value": REPORT_VALUES_RY[(material, config)],
        "failure_signals": None,
    }


def _compute_delta(a, b):
    """
    Computes the AFM-FM energy difference from the parsed SCF energies.

    Returns None if one of the calculations did not converge so the caller
    can fall back to the reported value.
    """
    if a["value"] is None or b["value"] is None:
        return None
    return (a["value"] - b["value"]) * RY_TO_MEV / NAT_ATOMS


def build_calibration_materials():
    materials = {}
    for name in CALIBRATION_ORDER:
        a = _leg(name, "AFM")
        b = _leg(name, "FM")
        a["label"], b["label"] = "AFM", "FM"

        computed_delta = _compute_delta(a, b)
        if computed_delta is not None:
            delta = computed_delta
            delta_source = "computed_from_raw_energies"
        else:
            delta = REPORT_DELTAS_MEV_PER_ATOM[name]
            delta_source = "real_report"

        materials[name] = {
            "cations": ["Mn", X_SITE_CATIONS[name], "W"],
            "candidate_a": a,
            "candidate_b": b,
            "delta": delta,
            "delta_source": delta_source,
            "source": "real_raw_output" if (a["source"] == "real_raw_output" and b["source"] == "real_raw_output")
            else "mixed" if (a["source"] == "real_raw_output" or b["source"] == "real_raw_output")
            else "real_report",
        }
    return materials


CALIBRATION_MATERIALS = build_calibration_materials()

# New candidates the calibration set has never run. Cd is real and
# chemically valid (CdWO4 is a known wolframite-type tungstate); Cd2+ is
# d10, the same shell filling as Zn2+, the only other d10 case here.
# UnknownXWO4 is synthetic - an invented d3 cation with no calibration
# analog, exercising the no-analog escalation path.
NEW_CANDIDATES = {
    "MnCdWO4": {"source": "real_cation_no_prior_run", "x_cation": "Cd", "x_d_shell": 10},
    "UnknownXWO4": {"source": "synthetic", "x_cation": "Xx", "x_d_shell": 3},
}
