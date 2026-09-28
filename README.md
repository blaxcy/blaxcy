# BLAXCY

Foreground device-control runtime with a GitHub-centered recovery/control bridge.

## Architecture

The repository contains the complete recoverable implementation. No permanent BLAXCY background agent is required.

    GitHub repository
          ↓
    clone + setup
          ↓
    foreground BLAXCY runtime
       ↙       ↓       ↘
     EYE     MOUSE   KEYBOARD
          ↕
    GitHub control mailbox
          ↕
       ChatGPT

The GitHub bridge uses an Issue's comments as a durable command mailbox. The device polls for structured commands and posts structured results. This removes the need for a separately hosted permanent relay for command/control.

GitHub is not a millisecond realtime media transport. The bridge is therefore a control/recovery channel, not a high-frequency video transport.

## Local mode

    python -m blaxcy connect

This starts the existing authenticated loopback WebSocket for a low-latency local client.

## GitHub bridge

The bridge uses one GitHub Issue as the mailbox.

Set these environment variables on the device. Never commit the token:

    BLAXCY_GITHUB_REPOSITORY=blaxcy/blaxcy
    BLAXCY_GITHUB_ISSUE=<issue number>
    BLAXCY_GITHUB_TOKEN=<fine-grained token>
    BLAXCY_GITHUB_ALLOWED_ACTOR=blaxcy

Then run:

    python -m blaxcy github-bridge

A command is a GitHub Issue comment beginning with:

    BLAXCY_CMD {"id":"cmd-1","command":{"action":"mouse.click","x":820,"y":430}}

The device posts:

    BLAXCY_RESULT {"id":"cmd-1","ok":true,"result":{...}}

Only the existing structured mouse/keyboard command executor is exposed. Arbitrary shell execution is not available.

GitHub's REST API supports reading and creating Issue comments; fine-grained tokens can be restricted to the repository Issues permission needed by this bridge.

## Security

Use a private repository for a real control mailbox. Issue comments on a public repository are publicly readable, so the current public blaxcy/blaxcy repository should be treated as development-only for this bridge until its visibility is changed.

The device keeps the GitHub token outside the repository, checks the GitHub actor before accepting commands, and uses the existing bounded command executor.

## Recovery

The source, bridge, protocol, device runtime, and setup code live in the repository. A replacement device can clone the repository and recreate the runtime without relying on the lost device.

## EYE status

EYE continuously captures the screen, performs pixel-change detection, tracks cursor changes, maintains revisions, emits dirty-region deltas, and periodically emits semantic keyframes. It remains local-first; the GitHub bridge should carry control/state summaries rather than raw high-frequency frames.

A true realtime visual stream still requires a realtime media transport; GitHub comments are intentionally not used as a fake video stream.
