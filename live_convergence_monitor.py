CONVERGENCE_THRESHOLD_RY = 1.0e-9
STALL_WINDOW = 10  # iterations without a new best before escalating


class SCFLiveMonitorAgent:
    """
    Monitors an SCF run while it is still executing.

    The agent reads one iteration at a time and decides whether to keep
    waiting, stop because convergence has been reached, or escalate because
    the calculation appears to have stalled.

    The stall threshold is based on the MnCoWO4 AFM trace. That run contains
    a temporary iteration plateau before converging, so the threshold
    is intentionally set above that to avoid stopping a calculation that is
    still making progress.
    """


    def run(self, trace):
        decisions = []
        best_so_far = None
        stall_count = 0

        for iteration, accuracy in trace:
            if accuracy < CONVERGENCE_THRESHOLD_RY:
                decisions.append((iteration, "CONCLUDE", f"{accuracy:.2e} Ry below threshold"))
                return decisions, "CONCLUDE"

            if best_so_far is None or accuracy < best_so_far:
                best_so_far = accuracy
                stall_count = 0
            else:
                stall_count += 1

            if stall_count >= STALL_WINDOW:
                decisions.append((
                    iteration,
                    "ESCALATE",
                    f"{STALL_WINDOW} iterations without beating best-so-far ({best_so_far:.2e} Ry)",
                ))
                return decisions, "ESCALATE"

            decisions.append((iteration, "CONTINUE", f"{accuracy:.2e} Ry, best so far {best_so_far:.2e} Ry"))

        decisions.append((trace[-1][0], "ESCALATE", "trace ended without reaching threshold"))
        return decisions, "ESCALATE"
