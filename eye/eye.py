#!/usr/bin/env python3
"""
EYE — realtime full-screen capture and change detector.

Design target:
- Capture the complete virtual desktop.
- Sample at a target interval of 10 ms (100 Hz).
- Detect even small pixel changes between consecutive frames.
- Emit changed/full frames through a simple stdout protocol for the next
  transport layer.

This first version deliberately does NOT control the device and does NOT
execute arbitrary commands.
"""

from __future__ import annotations

import argparse
import sys
import time

import mss
import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BLAXCY EYE realtime screen watcher")
    p.add_argument("--interval-ms", type=float, default=10.0)
    p.add_argument("--monitor", type=int, default=0,
                   help="mss monitor index; 0 means the complete virtual desktop")
    p.add_argument("--threshold", type=int, default=0,
                   help="per-channel absolute pixel threshold for change detection")
    return p.parse_args()


def frame_changed(previous: np.ndarray | None, current: np.ndarray, threshold: int) -> bool:
    if previous is None or previous.shape != current.shape:
        return True

    if threshold <= 0:
        return bool(np.any(previous != current))

    delta = np.abs(current.astype(np.int16) - previous.astype(np.int16))
    return bool(np.any(delta > threshold))


def main() -> int:
    args = parse_args()

    if args.interval_ms <= 0:
        raise SystemExit("--interval-ms must be > 0")

    interval = args.interval_ms / 1000.0
    previous = None
    frames = 0
    changed = 0
    started = time.perf_counter()
    next_tick = started

    with mss.mss() as sct:
        monitor = sct.monitors[args.monitor]

        print(
            "EYE_READY "
            f"monitor={args.monitor} "
            f"left={monitor['left']} top={monitor['top']} "
            f"width={monitor['width']} height={monitor['height']} "
            f"interval_ms={args.interval_ms:g}",
            flush=True,
        )

        try:
            while True:
                now = time.perf_counter()

                if now < next_tick:
                    time.sleep(next_tick - now)

                shot = np.asarray(sct.grab(monitor), dtype=np.uint8)
                # MSS returns BGRA; keep the alpha channel out of comparisons.
                current = shot[:, :, :3]

                frames += 1
                if frame_changed(previous, current, args.threshold):
                    changed += 1
                    # Transport is intentionally left to the next EYE layer.
                    # This marker proves that the frame changed.
                    print(
                        f"EYE_FRAME_CHANGED frame={frames} "
                        f"t_ns={time.perf_counter_ns()}",
                        flush=True,
                    )

                previous = current
                next_tick += interval

                # Recover cleanly if processing ever falls far behind.
                if next_tick < time.perf_counter() - interval:
                    next_tick = time.perf_counter()

        except KeyboardInterrupt:
            elapsed = max(time.perf_counter() - started, 1e-9)
            print(
                f"EYE_STOP frames={frames} changed={changed} "
                f"avg_fps={frames / elapsed:.2f}",
                file=sys.stderr,
            )
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
