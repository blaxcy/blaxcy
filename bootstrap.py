from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    extras = []
    if sys.platform.startswith("win"):
        extras.append("windows")
    elif sys.platform == "darwin":
        extras.append("macos")
    elif sys.platform.startswith("linux"):
        extras.append("linux")

    target = str(root) + (f"[{','.join(extras)}]" if extras else "")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", target])
    print("\nBLAXCY installed with native accessibility support when available.")
    print("Start: python -m blaxcy connect")
    print("MCP:   python -m blaxcy.mcp_server")
    print("GitHub control: python -m blaxcy github-bridge")


if __name__ == "__main__":
    main()
