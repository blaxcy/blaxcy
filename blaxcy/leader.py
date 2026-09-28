from __future__ import annotations

"""Local command leader.

It watches the GitHub-synced command file, validates commands, executes them,
and writes an acknowledgement. It never executes arbitrary shell commands.
"""

import argparse
import time

from .github_bridge import process_once


def main() -> None:
    p = argparse.ArgumentParser(description="BLAXCY command leader")
    p.add_argument("--width", type=int, required=True)
    p.add_argument("--height", type=int, required=True)
    p.add_argument("--poll", type=float, default=0.25)
    args = p.parse_args()

    last_id: str | None = None
    while True:
        last_id = process_once(args.width, args.height, last_id)
        time.sleep(max(0.05, args.poll))


if __name__ == "__main__":
    main()
