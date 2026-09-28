# BLAXCY

Temporary foreground device-control runtime.

## Core tools

- EYE — continuous screen feed, change detection, persistent current state, delta updates.
- MOUSE — structured mouse actions.
- KEYBOARD — structured keyboard actions.

There is no permanent background agent. The runtime exists only while the connection command is running.

## Start

    python -m venv .venv
    pip install -e .
    python -m blaxcy connect

Stop the foreground session with Ctrl+C.

## EYE model

    continuous capture
          ↓
    change detection
          ↓
    dirty regions
          ↓
    persistent screen state
          ↓
    delta events

EYE does not intentionally send every raw frame to the reasoning layer. It maintains a current state and emits meaningful changes, with periodic keyframes.

The first implementation establishes the local runtime/protocol foundation. OS-specific accessibility semantics, OCR, and the remote ChatGPT transport are layered onto this protocol.

## Security

The public repository contains no device credentials or API keys. The local session is explicitly started by the user and ends when the process exits. Remote transport must authenticate a session before accepting MOUSE/KEYBOARD commands.
