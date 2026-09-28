# BLAXCY

BLAXCY is a recoverable, foreground-only device-control runtime. The GitHub repository is the recovery/source-of-truth package: a new device can recreate the runtime from the repo without depending on the old device.

Temporary foreground device-control runtime.

## Architecture

A user starts one foreground command. While it is running:

    DEVICE SCREEN
         ↓
    continuous capture
         ↓
    pixel/change detection
         ↓
    persistent EYE state
         ↓
    live delta/keyframe events
         ↓
    authenticated local transport
         ↓
    structured MOUSE / KEYBOARD commands

There is no permanent background agent.

## Start

    git clone https://github.com/blaxcy/blaxcy.git
    cd blaxcy
    python -m venv .venv

Activate the virtual environment, then:

    python -m pip install -e .
    python -m blaxcy connect

Optional OCR:

    python -m pip install pytesseract
    python -m blaxcy connect --ocr

Stop with Ctrl+C.

## Pairing and connector contract

Every foreground session creates a fresh device/session identity and a fresh short-lived control token. The token is stored locally in `.blaxcy/pairing.json` with restrictive permissions where the platform supports them. The repository never contains a device secret.

`blaxcy.chatgpt.tool_manifest()` exposes the stable ChatGPT-facing capability contract, while `blaxcy.gateway.GatewayEnvelope` defines a transport-neutral authenticated message envelope. A connector/relay can implement this contract without changing the device runtime.

## Local transport

The foreground process opens an authenticated WebSocket on loopback by default:

    ws://127.0.0.1:8765

The startup event prints a random session token. A client must authenticate with:

    {"type":"auth","token":"..."}

After authentication it can receive live EYE keyframe/delta/cursor events and send structured MOUSE/KEYBOARD commands.

Examples:

    {"type":"state.get"}

    {"type":"command","action":"mouse.click","x":820,"y":430}

    {"type":"command","action":"keyboard.type","text":"hello"}

The transport intentionally binds to 127.0.0.1 by default. Do not expose it publicly without adding a secure authenticated relay.

## EYE

EYE continuously captures the screen and compares consecutive frames. Small changes produce dirty-region deltas instead of sending the entire frame to the reasoning layer. Periodic keyframes rebuild semantic state.

Semantic perception currently supports optional OCR and screen geometry. OS accessibility adapters can be added without changing the control protocol.

The 1–5 ms change-detection target is a performance target, not a guarantee. Capture latency is constrained by display refresh rate, operating system capture APIs, hardware, resolution, and system load.

## Security

- No credentials are stored in the repository.
- The device runtime is foreground-only.
- The local control channel requires a random per-session token.
- Commands are structured and bounded; arbitrary shell execution is not exposed.
- Ctrl+C stops the session.
- Keep the default loopback binding unless a separately secured relay is implemented.

## ChatGPT integration boundary

GitHub is the source repository, not a realtime screen transport. The runtime therefore uses a temporary low-latency local channel while the repo provides the code and configuration.

A ChatGPT deployment must have an explicitly configured connector/relay capable of reaching the running session before it can consume the live EYE stream or issue local commands. Merely connecting the GitHub repository does not by itself grant ChatGPT access to a user's localhost process.
