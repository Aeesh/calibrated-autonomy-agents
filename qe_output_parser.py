import re


def parse_scf_output(path):
    """Reads final total energy, convergence iteration count, and wall
    time from a Quantum ESPRESSO scf.out file. Values come from the
    LAST matching line in the file, i.e. the final relaxation step for
    a structural optimization run."""
    with open(path) as f:
        text = f.read()

    result = {"converged": False, "E_Ry": None, "iterations_to_converge": None, "wall_seconds": None}

    final_energy_matches = re.findall(r"!\s*total energy\s*=\s*(-?\d+\.\d+)\s*Ry", text)
    if final_energy_matches:
        result["E_Ry"] = float(final_energy_matches[-1])

    conv_matches = re.findall(r"convergence has been achieved in\s*(\d+)\s*iterations", text)
    if conv_matches:
        result["converged"] = True
        result["iterations_to_converge"] = int(conv_matches[-1])

    wall_match = re.search(r"PWSCF\s*:\s*[\dms\. ]+CPU\s*(\d+)m\s*([\d.]+)s\s*WALL", text)
    if wall_match:
        minutes, seconds = wall_match.groups()
        result["wall_seconds"] = int(minutes) * 60 + float(seconds)

    return result
