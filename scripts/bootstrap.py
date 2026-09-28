from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(*args: str) -> None:
    subprocess.check_call(list(args))


def main() -> int:
    if not VENV.exists():
        run(sys.executable, "-m", "venv", str(VENV))

    run(str(PYTHON), "-m", "pip", "install", "--upgrade", "pip")
    run(str(PYTHON), "-m", "pip", "install", "-e", str(ROOT))

    extra = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    if extra:
        try:
            run(str(PYTHON), "-m", "pip", "install", "-e", f"{ROOT}[{extra}]")
        except subprocess.CalledProcessError:
            print(
                f"BLAXCY: optional {extra} accessibility package could not be installed; "
                "continuing with pixel/OCR perception.",
                file=sys.stderr,
            )

    try:
        run(str(PYTHON), "-m", "pip", "install", "-e", f"{ROOT}[ocr]")
    except subprocess.CalledProcessError:
        print("BLAXCY: optional OCR package could not be installed.", file=sys.stderr)

    run(str(PYTHON), "-m", "blaxcy", "connect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
