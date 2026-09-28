from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> int:
    if not VENV.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    subprocess.check_call([str(PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(PYTHON), "-m", "pip", "install", "-e", str(ROOT)])
    os.execv(str(PYTHON), [str(PYTHON), "-m", "blaxcy", "connect"])


if __name__ == "__main__":
    raise SystemExit(main())
