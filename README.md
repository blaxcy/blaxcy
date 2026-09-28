# BLAXCY

BLAXCY is a recoverable, foreground-only device-control runtime. The GitHub repository is the source-of-truth and recovery point: a new device recreates the runtime from the repo without depending on the old device.

## Architecture

    GitHub repo
        ↓
    one-command bootstrap
        ↓
    foreground BLAXCY runtime
        ├── EYE
        │    ├── continuous capture
        │    ├── pixel/change detection
        │    ├── changed-region JPEGs
        │    ├── full visual keyframes
        │    ├── frame hashes
        │    ├── accessibility/UI semantics
        │    └── optional OCR
        ├── MOUSE
        ├── KEYBOARD
        └── authenticated local WebSocket
                 ↓
          repo-provided MCP connector
                 ↓
              ChatGPT

There is no permanent background agent. The device is controllable only while the foreground session is running.

## One-command setup

    git clone https://github.com/blaxcy/blaxcy.git
    cd blaxcy
    python scripts/bootstrap.py

The bootstrap creates `.venv`, installs the repo, creates a fresh pairing credential, and starts the foreground runtime.

Optional OCR:

    python -m pip install -e '.[ocr]'
    python -m blaxcy connect --ocr

Platform accessibility support:

    Windows:  python -m pip install -e '.[windows]'
    Linux:    python -m pip install -e '.[linux]'
    macOS:    python -m pip install -e '.[macos]'

Native accessibility may additionally require OS permission/configuration. If it is unavailable, EYE falls back to pixel perception and optional OCR.

## ChatGPT connector

The repo contains an MCP server:

    python -m blaxcy mcp

or:

    blaxcy-mcp

The default transport is stdio, intended for an MCP host that launches the connector locally. Streamable HTTP is also available:

    python -m blaxcy mcp --transport streamable-http

The connector exposes:

- `eye_state` — semantic state, cursor, revision and frame hash
- `eye_snapshot` — current visual keyframe as MCP image content
- `eye_events` — incremental EYE keyframes/deltas/cursor updates after a revision
- `mouse_move`
- `mouse_click`
- `mouse_scroll`
- `keyboard_press`
- `keyboard_hotkey`
- `keyboard_type`

The connector reads the fresh token from `.blaxcy/pairing.json` and authenticates to the foreground runtime. Arbitrary shell execution is not exposed.

A ChatGPT deployment still has to be configured to use this MCP server. The repository contains the connector implementation and all device-side logic, but a GitHub repository alone cannot register a tool with ChatGPT or make ChatGPT reach a user's localhost process automatically. For remote ChatGPT access, use a supported authenticated MCP hosting/tunnel mechanism. Streamable HTTP should never be exposed publicly without authentication and HTTPS.

## EYE

EYE continuously captures the primary display and compares consecutive frames. Normal changes send only dirty regions encoded as JPEG crops. Large changes trigger a full keyframe. Periodic resyncs rebuild semantic state and include a frame hash.

Each visual update carries revision information so an MCP client can poll `eye_events` incrementally instead of requesting a full screen every time.

Semantic perception combines:

- native OS accessibility/UI trees where available
- OCR when enabled
- screen geometry
- pixel evidence
- stable semantic element IDs

Native adapters:

- Windows UI Automation via pywinauto
- Linux AT-SPI via pyatspi
- macOS Accessibility via PyObjC/Quartz

If native accessibility is unavailable or permission is denied, EYE continues with pixels/OCR.

The 1–5 ms change-detection target is a performance target, not a guarantee. Capture latency is constrained by display refresh rate, OS capture APIs, hardware, resolution, and system load. A 60 Hz display cannot provide genuinely new visual information every 1–5 ms.

## Pairing and recovery

Every foreground session creates a fresh device/session identity and control token. The token is stored locally in `.blaxcy/pairing.json`; it is never committed to GitHub.

Losing the old device does not lose the system:

    clone repository
    run bootstrap
    fresh session credential is generated

No permanent device agent is required.

## Local transport

The foreground process opens:

    ws://127.0.0.1:8765

Authentication requires a fresh per-session token. The transport supports:

- authenticated state retrieval
- incremental EYE event replay
- live EYE broadcasts
- structured mouse/keyboard commands

The default binding is loopback. Do not expose it publicly.

## Security

- foreground-only runtime
- fresh per-session token
- token never committed to GitHub
- constant-time token comparison
- bounded structured commands
- no arbitrary shell execution
- loopback by default
- explicit MCP/tunnel configuration for remote ChatGPT access
- Ctrl+C stops the session