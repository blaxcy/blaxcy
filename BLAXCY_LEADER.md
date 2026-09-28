# BLAXCY Leader

## Purpose
This file is the machine-readable handoff/control plan for the BLAXCY project.

## Current objective
Complete the repo-contained pieces that are technically implementable:
1. Production-oriented EYE pipeline.
2. Accessibility/semantic adapter framework where the host OS supports it.
3. ChatGPT-facing connector protocol and capability manifest.
4. Secure device session/pairing and transport abstraction.
5. One-command bootstrap/recovery.
6. Tests and CI.

## Architecture
GitHub repository is the recoverable source of truth. The repository contains all implementation needed to bootstrap a new device.

Device runtime:
EYE -> state/delta -> connector transport
ChatGPT connector -> authenticated session -> commands -> device

GitHub is NOT treated as a millisecond realtime socket. A runtime communication channel is used by code contained in this repository.

## Current known limitations
- A native ChatGPT connector cannot be created solely by committing files to GitHub; ChatGPT-side connector registration/runtime support is external to the repository.
- OS accessibility APIs differ by platform and require host-specific adapters.
- Screen capture latency is constrained by OS/display/hardware; 1–5 ms is a target, not a guarantee.

## Required implementation
- Keep secrets out of Git.
- Short-lived per-session credentials.
- Foreground runtime and explicit stop.
- No arbitrary shell execution.
- EYE keyframes + changed-region payloads + state recovery.
- Capability discovery endpoint/message.
- Versioned protocol.
- Bootstrap command that installs dependencies and starts the runtime.
- Connector documentation describing the exact external ChatGPT-side step, without pretending GitHub alone provides live transport.

## Definition of done
A fresh device can clone the repo and run one documented command to install/start BLAXCY; the runtime exposes authenticated EYE/MOUSE/KEYBOARD capabilities through its connector protocol; all repo-contained functionality is tested; remaining external dependency is only the ChatGPT-side connector registration/transport access that cannot be provisioned by GitHub files alone.

## Instruction to the implementing agent
Read this file first. Inspect the repository before changing it. Implement every item above that is possible inside the repository. Update this file with completed items and remaining blockers. Do not claim an external ChatGPT connector exists unless it is actually configured and verified.
