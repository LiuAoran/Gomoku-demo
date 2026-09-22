import os
from pathlib import Path
import shlex

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_jev_key(path=None):
    """Read only the TypeSafe key, without executing or changing environment variables."""
    if "TYPESAFE_API_KEY" in os.environ:
        return os.environ["TYPESAFE_API_KEY"].strip()
    try:
        lines = Path(path or ENV_FILE).read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return ""
    for line in lines:
        name, separator, value = line.strip().removeprefix("export ").partition("=")
        if not separator or name.strip() != "TYPESAFE_API_KEY":
            continue
        try:
            parts = shlex.split(value, comments=True)
        except ValueError:
            return ""
        return parts[0] if len(parts) == 1 else ""
    return ""
