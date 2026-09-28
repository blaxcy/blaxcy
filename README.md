# BLAXCY

Recoverable foreground device-control runtime with EYE, MOUSE, KEYBOARD, native accessibility and an MCP connector.

## Architecture

The repository contains the recoverable implementation. A replacement device can clone it and recreate the runtime without depending on the lost device.

    GitHub repository
          ↓
    clone + one bootstrap command
          ↓
    BLAXCY runtime
       ↙       ↓       ↘
     EYE     MOUSE   KEYBOARD
       ↕
    local authenticated transport
       ↕
    BLAXCY MCP connector

## Install

After cloning:

    python bootstrap.py

Then:

    python -m blaxcy connect

The MCP server can start the runtime automatically when it is invoked:

    blaxcy-mcp

A client that supports MCP can use .mcp.json as the local server configuration.

## ChatGPT connection

The repository now contains the BLAXCY MCP server and the complete device-side protocol. It exposes:

- system_status
- eye_state
- eye_snapshot
- eye_events
- mouse_move
- mouse_click
- mouse_scroll
- keyboard_press
- keyboard_hotkey
- keyboard_type

The MCP server starts/reaches the foreground runtime locally and authenticates with a per-session pairing file.

Important: a repository cannot automatically register itself as a ChatGPT connector. The final ChatGPT-side step still requires the ChatGPT environment to be configured to use this MCP server. The connector implementation itself is now in the repository.

## EYE

EYE continuously captures the screen, performs pixel-change detection, tracks cursor changes, maintains revisions, emits semantic keyframes and JPEG visual keyframes, and emits JPEG patches for changed regions.

The semantic layer combines:

- Windows UI Automation through pywinauto
- Linux AT-SPI through pyatspi
- macOS Accessibility APIs through PyObjC/Quartz
- optional OCR
- pixel geometry

Install platform extras when required:

    pip install -e ".[windows]"
    pip install -e ".[linux]"
    pip install -e ".[macos]"
    pip install -e ".[ocr]"

Native accessibility APIs may require OS-level Accessibility/AT-SPI permission.

## GitHub control bridge

The repository also contains a GitHub-backed command mailbox:

    python -m blaxcy github-bridge

The device reads `.blaxcy/command.json` from the configured repository and
writes the acknowledgement to `.blaxcy/command_ack.json`. Commands are
schema-validated and limited to mouse/keyboard actions.

Authentication is taken from `GITHUB_TOKEN` or, when available, `gh auth token`.
The token is never written into the repository. For a private repository, a
fine-grained token with only the required Contents permissions is sufficient.
GitHub's Contents API supports reading repository files and creating/updating
files; authenticated requests have substantially higher rate limits than
unauthenticated requests. citeturn1search1turn0search0

This channel is a **control/recovery plane**, not a realtime video transport.
GitHub recommends avoiding aggressive polling; BLAXCY therefore uses conditional
requests and a conservative default interval. citeturn0search3

Example command written by the ChatGPT/GitHub side:

    {
      "id": "cmd-001",
      "actor": "blaxcy",
      "action": "mouse.click",
      "x": 820,
      "y": 430
    }

Then the device executes it and writes the result to the acknowledgement file.

## Security

- foreground device runtime
- random per-session pairing token
- pairing file kept outside Git history
- loopback-only local WebSocket by default
- bounded mouse/keyboard commands
- no arbitrary shell execution
- MCP does not expose the pairing token
- Ctrl+C stops the runtime

## Current boundary

The repo-side implementation is now complete for the device runtime, EYE visual/semantic layer, local MCP connector, pairing and GitHub control mailbox.

The remaining external step is connecting that MCP server to the particular ChatGPT environment. That registration cannot be performed by code committed to GitHub alone.
