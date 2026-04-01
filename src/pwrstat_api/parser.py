import re
import subprocess
from pathlib import Path

PWRSTAT_BINARY = "/usr/sbin/pwrstat"
SUBPROCESS_TIMEOUT = 10  # seconds

# Matches lines like: "Model Name................... CP1500PFCLCD"
# Key: text before dots, Value: text after dots+whitespace
_LINE_PATTERN = re.compile(r"^(.+?)\s*\.{2,}\s+(.+)$")


class PwrstatError(Exception):
    pass


def get_pwrstat_status() -> dict[str, str]:
    """Run pwrstat -status and return parsed key-value pairs.

    Raises:
        FileNotFoundError: if pwrstat binary is missing.
        subprocess.TimeoutExpired: if pwrstat takes too long.
        PwrstatError: if pwrstat exits with a non-zero code.
    """
    if not Path(PWRSTAT_BINARY).is_file():
        raise FileNotFoundError(f"pwrstat binary not found at {PWRSTAT_BINARY}")

    result = subprocess.run(
        [PWRSTAT_BINARY, "-status"],
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
    )

    if result.returncode != 0:
        raise PwrstatError(f"pwrstat exited with code {result.returncode}")

    return _parse_output(result.stdout)


def _parse_output(output: str) -> dict[str, str]:
    """Parse pwrstat -status output into a dictionary.

    Uses a regex to match lines with the "Key......... Value" pattern,
    preserving values that themselves contain dots (e.g. firmware numbers).
    """
    status: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        match = _LINE_PATTERN.match(line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key and value:
                status[key] = value
    return status
