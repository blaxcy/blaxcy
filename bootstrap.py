from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(root)])
    print("\nBLAXCY installed.")
    print("Start: python -m blaxcy connect")
    print("MCP:   blaxcy-mcp")


if __name__ == "__main__":
    main()
