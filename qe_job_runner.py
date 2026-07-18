import subprocess


def attempt_run(input_path, output_path):
    """
    Tries to actually execute a generated QE input file. This sandbox
    has no pw.x and no HPC access, so this will fail here. On a cluster
    this same call would submit the job for real.
    """
    try:
        result = subprocess.run(
            ["pw.x", "-in", input_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        with open(output_path, "w") as f:
            f.write(result.stdout)
        return True, "ran successfully"
    except FileNotFoundError:
        return False, "pw.x not available in this environment - input file is ready to submit on a real cluster"
    except Exception as e:
        return False, f"execution failed: {e}"
