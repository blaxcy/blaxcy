# BLAXCY

BLAXCY is a recoverable, foreground-only device-control runtime. The GitHub repository is the source-of-truth and recovery point: a new device can recreate the software from the repo without depending on the old device.

## Architecture

    GitHub repo
        ↓
    one-command bootstrap
        ↓
    foreground BLAXCY runtime
        ├── EYE
        │    ├── continuous screen capture
        │    ├── pixel/change detection
        │    ├── changed-region JPEGs
        │    ├── full visual keyframes
        │    ├── frame hashes
        │    ├── native accessibility/UI semantics
        │    └── optional OCR
        ├── MOUSE
        ├── KEYBOARD
        └── authenticated loopback transport
                 ↓
          repo-provided MCP connector
                 ↓
              ChatGPT / MCP host

There is no permanent background agent. Device control exists only while the foreground runtime is running.

## One-command recovery

    git clone https://github.com/blaxcy/blaxcy.git
    cd blaxcy
    python scripts/bootstrap.py

The bootstrap creates the virtual environment, installs the repository and starts a fresh foreground session. Session credentials are generated locally and are ignored by Git.

The repository is the recovery point: losing the old device does not remove the source code or setup logic.

## ChatGPT / MCP connector

BLAXCY includes an MCP server:

    python -m blaxcy mcp

or:

    blaxcy-mcp

Default transport is stdio. This is intended for an MCP host that launches the connector as a local subprocess.

For a remotely reachable MCP endpoint:

    python -m blaxcy mcp --transport streamable-http

The MCP server exposes:

- `system_status`
- `eye_state`
- `eye_snapshot`
- `eye_events`
- `mouse_move`
- `mouse_click`
- `mouse_scroll`
- `keyboard_press`
- `keyboard_hotkey`
- `keyboard_type`

The connector automatically starts the foreground BLAXCY runtime if one is not already reachable. It authenticates to that runtime using the fresh local pairing token. The secret token is never returned by the MCP tools and is never committed to GitHub.

The current MCP implementation is a complete repository-side connector. **ChatGPT itself still needs to be configured to use the MCP server.** ChatGPT connects to remote MCP servers; it cannot directly reach a local MCP server. OpenAI documents Secure MCP Tunnel for connecting a local/private MCP server without exposing it publicly. Custom MCP apps are configured with an endpoint and authentication in supported ChatGPT developer-mode/app environments. 

For remote HTTP, keep the server behind HTTPS and an authenticated tunnel/deployment. The repository defaults to loopback and does not expose the device to the public internet.

## EYE

EYE continuously captures the primary display. It compares consecutive frames locally and normally sends only changed regions. Changed regions are JPEG crops; large changes trigger a complete visual keyframe.

Every update carries a monotonic revision and frame hash. The connector can request only events after a known revision, so the model does not need a full screenshot on every update.

The semantic layer combines:

- Windows UI Automation when `pywinauto` is installed
- Linux AT-SPI when `pyatspi` is installed and available
- macOS accessibility hook when a platform adapter is available
- OCR when `pytesseract` is installed
- pixel geometry and visual evidence
- stable semantic element IDs
- actionable-element metadata

Native accessibility is best-effort because each operating system can require user permissions and platform-specific runtime components. If native accessibility is unavailable, EYE continues using pixels and optional OCR.

The 1–5 ms change-detection number is a local processing target, not a guaranteed end-to-end visual latency. Display refresh rate, capture APIs, hardware, resolution and OS scheduling limit the actual rate of new information.

## Pairing and recovery

Every foreground session creates:

- a fresh device ID
- a fresh session ID
- a fresh random control token

The token is stored only in `.blaxcy/pairing.json`, which is ignored by Git.

The old device can therefore disappear without taking the system with it:

    new device
      ↓
    clone repo
      ↓
    bootstrap
      ↓
    fresh credentials
      ↓
    fresh BLAXCY session

## Local control protocol

The runtime listens on:

    ws://127.0.0.1:8765

Authentication is required before any state or command operation.

Supported protocol operations include:

    {"type":"state.get"}
    {"type":"events.get","revision":123}
    {"type":"command","action":"mouse.click","x":820,"y":430}
    {"type":"command","action":"keyboard.type","text":"hello"}

No arbitrary shell execution is exposed.

## Security

- foreground-only runtime
- fresh per-session token
- token never committed to GitHub
- constant-time token comparison
- bounded mouse/keyboard commands
- no arbitrary shell execution
- loopback by default
- remote MCP only through explicit authenticated deployment/tunnel
- Ctrl+C stops the runtime

## Platform notes

Windows:

    python -m pip install -e '.[windows]'

Linux:

    python -m pip install -e '.[linux]'

macOS:

    python -m pip install -e '.[macos]'

Native accessibility permissions may still need to be granted in the operating system.

## Development

    python -m pip install -e .
    python -m pytest -q

GitHub Actions runs the test suite on pushes and pull requests.
