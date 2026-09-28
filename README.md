# BLAXCY

BLAXCY is a recoverable, foreground-only device-control runtime. The GitHub repository is the recovery/source-of-truth package: a new device can recreate the runtime from the repo without depending on the old device.

## Architecture

    GitHub repo
        ↓
    one-command bootstrap
        ↓
    foreground BLAXCY runtime
        ├── EYE
        │    ├── continuous capture
        │    ├── pixel deltas
        │    ├── changed-region JPEGs
        │    ├── keyframes
        │    └── accessibility + OCR semantics
        ├── MOUSE
        ├── KEYBOARD
        └── local authenticated WebSocket
                 ↓
          BLAXCY MCP connector
                 ↓
             ChatGPT

There is no permanent background agent. The device is controllable only while the foreground session is running.

## One-command setup

    git clone https://github.com/blaxcy/blaxcy.git
    cd blaxcy
    python scripts/bootstrap.py

The bootstrap creates .venv, installs the repo, and starts the foreground runtime.

Optional platform perception packages:

    python -m pip install -e '.[windows]'
    python -m pip install -e '.[linux]'
    python -m pip install -e '.[macos]'
    python -m pip install -e '.[ocr]'

## ChatGPT connector

The repo contains an MCP server:

    python -m blaxcy mcp

or:

    blaxcy-mcp

The default transport is stdio, suitable for an MCP host that launches the connector locally. A Streamable HTTP server is also available:

    python -m blaxcy mcp --transport streamable-http

The MCP tools are:
- eye_state
- mouse_move
- mouse_click
- mouse_scroll
- keyboard_press
- keyboard_hotkey
- keyboard_type

The MCP server authenticates to the running BLAXCY runtime using the fresh per-session token in .blaxcy/pairing.json. It never exposes arbitrary shell execution.

For ChatGPT, a local/private MCP server can be connected through a supported Secure MCP Tunnel; alternatively the MCP server can be deployed behind a properly authenticated HTTPS endpoint. ChatGPT does not gain localhost access merely because this GitHub repository is connected. The repository contains the connector implementation and recovery logic, while the ChatGPT-side tunnel/host configuration is explicit.

## EYE

EYE continuously captures the screen and compares consecutive frames. Normal changes send only dirty regions encoded as JPEG crops. Large changes trigger a full keyframe. Periodic resyncs rebuild semantic state and include a frame hash.

Semantic perception combines:
- native OS accessibility/UI trees where available
- OCR when enabled
- screen geometry
- pixel evidence

Native adapters are optional:
- Windows UI Automation via pywinauto
- Linux AT-SPI via pyatspi
- macOS Accessibility via PyObjC/Quartz

If native accessibility is unavailable or permission is denied, EYE continues with pixels/OCR.

The 1–5 ms change-detection target is a performance target, not a guarantee. Capture latency is constrained by display refresh rate, operating system capture APIs, hardware, resolution, and system load.

## Pairing and recovery

Every foreground session creates a fresh device/session identity and control token. The token is stored locally in .blaxcy/pairing.json; it is never committed to GitHub.

Losing the old device does not lose the system: clone the repository on a new device and run the bootstrap again. A fresh session credential is generated.

## Local transport

The foreground process opens:

    ws://127.0.0.1:8765

Authentication requires:

    {"type":"auth","token":"..."}

After authentication the client can receive EYE keyframe/delta/cursor events and issue structured mouse/keyboard commands.

## Security

- foreground-only runtime
- fresh per-session token
- local secret never committed to the repo
- bounded structured commands
- no arbitrary shell execution
- loopback by default
- explicit MCP/tunnel configuration for remote ChatGPT access
- Ctrl+C stops the session
