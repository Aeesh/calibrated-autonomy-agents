import re

ITER_RE = re.compile(r"iteration #\s*(\d+)")
ACC_RE = re.compile(r"estimated scf accuracy\s*<\s*([\d.eE+-]+)\s*Ry")
CONVERGED_RE = re.compile(r"convergence has been achieved in\s*(\d+)\s*iterations")


def parse_first_scf_block(path):
    """Reads a Quantum ESPRESSO scf.out file, returns the first
    self-consistency block as (iteration, accuracy_ry) pairs, stopping at
    the first "convergence has been achieved" line. A relaxation run has
    one block per ionic step; the first block has the most iterations."""
    trace = []
    reported_convergence_iters = None
    with open(path) as f:
        pending_iter = None
        for line in f:
            m_iter = ITER_RE.search(line)
            if m_iter:
                pending_iter = int(m_iter.group(1))
                continue
            m_acc = ACC_RE.search(line)
            if m_acc and pending_iter is not None:
                trace.append((pending_iter, float(m_acc.group(1))))
                pending_iter = None
                continue
            m_conv = CONVERGED_RE.search(line)
            if m_conv:
                reported_convergence_iters = int(m_conv.group(1))
                break
    return trace, reported_convergence_iters
