import qe_constants as p

# ATOMIC_POSITIONS / CELL_PARAMETERS aren't in the source report, only
# the space group (P2/c) and atom count (12: 2 A-site, 2 X-site, 2 W,
# 6 O). Placeholder notes arw left in every generated file rather than
# fabricated coordinates.

A_SITE_MN_U_EV = 4.65


def _hubbard_block(x_cation, x_u_ev):
    lines = ["HUBBARD (ortho-atomic)", f"U Mn-3d {A_SITE_MN_U_EV:.2f}"]
    if x_u_ev is not None:
        lines.append(f"U {x_cation}-3d {x_u_ev:.2f}")
    return "\n".join(lines)


def _placeholder_note():
    return (
        "! ATOMIC_SPECIES, ATOMIC_POSITIONS, CELL_PARAMETERS: not in the source\n"
        "! report, fill in from the actual relaxed structure first."
    )


def known_fix_rerun(material, cations, fe_starting_magnetization=-0.50):
    """Generates the rerun input for the documented MnFeWO4 AFM fix."""
    return f"""\
&CONTROL
  calculation = 'scf'
  prefix = '{material}_AFM_recheck'
/
&SYSTEM
  ibrav = 0
  nat = 12
  ntyp = {len(cations)}
  ecutwfc = {p.ECUTWFC_RY}
  ecutrho = {p.ECUTRHO_RY}
  nspin = 2
  occupations = 'smearing'
  smearing = '{p.SMEARING}'
  degauss = {p.DEGAUSS_RY}
  starting_magnetization(1) = {fe_starting_magnetization}
/
&ELECTRONS
  conv_thr = {p.SCF_THRESHOLD_RY}
  mixing_beta = 0.3
  mixing_mode = 'local-TF'
  electron_maxstep = 200
/
{_hubbard_block('Fe', 5.30)}
K_POINTS automatic
  {p.KMESH_SCF[0]} {p.KMESH_SCF[1]} {p.KMESH_SCF[2]} 0 0 0

{_placeholder_note()}
"""


def recheck_denser_kmesh(material, cations, x_cation, x_u_ev):
    """ESCALATE_VERIFY_WORTHWHILE path: Creates the denser k-mesh rerun used for close AFM/FM cases."""
    return f"""\
&CONTROL
  calculation = 'scf'
  prefix = '{material}_recheck_densekmesh'
/
&SYSTEM
  ibrav = 0
  nat = 12
  ntyp = {len(cations)}
  ecutwfc = {p.ECUTWFC_RY}
  ecutrho = {p.ECUTRHO_RY}
  nspin = 2
  occupations = 'smearing'
  smearing = '{p.SMEARING}'
  degauss = {p.DEGAUSS_RY}
/
&ELECTRONS
  conv_thr = {p.SCF_THRESHOLD_RY}
  mixing_beta = 0.7
/
{_hubbard_block(x_cation, x_u_ev)}
K_POINTS automatic
  {p.KMESH_NSCF[0]} {p.KMESH_NSCF[1]} {p.KMESH_NSCF[2]} 0 0 0

! Denser mesh than the original SCF run ({p.KMESH_SCF}), reusing the
! NSCF density to check whether the energy ordering survives tighter
! k-sampling.
{_placeholder_note()}
"""


def new_candidate_scf(material, x_cation, x_u_ev, config_label):
    """First SCF for a candidate not in the calibration set. If x_u_ev
    is None, omits the X-site Hubbard line with no U applied on Zn."""
    cations = ["Mn", x_cation, "W"]
    u_note = f"U({x_cation}) = {x_u_ev:.2f} eV, by analogy" if x_u_ev is not None else f"no U applied to {x_cation}"
    return f"""\
&CONTROL
  calculation = 'scf'
  prefix = '{material}_{config_label}'
/
&SYSTEM
  ibrav = 0
  nat = 12
  ntyp = {len(cations)}
  ecutwfc = {p.ECUTWFC_RY}
  ecutrho = {p.ECUTRHO_RY}
  nspin = 2
  occupations = 'smearing'
  smearing = '{p.SMEARING}'
  degauss = {p.DEGAUSS_RY}
/
&ELECTRONS
  conv_thr = {p.SCF_THRESHOLD_RY}
  mixing_beta = 0.7
/
{_hubbard_block(x_cation, x_u_ev)}
K_POINTS automatic
  {p.KMESH_SCF[0]} {p.KMESH_SCF[1]} {p.KMESH_SCF[2]} 0 0 0

! {u_note}, not yet confirmed by linear response for this cation.
{_placeholder_note()}
"""
