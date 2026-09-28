from __future__ import annotations

import argparse
import asyncio
import signal
import threading

import mss

from .chatgpt import tool_manifest
from .eye import Eye, EyeConfig
from .pairing import create_pairing, fingerprint, save_pairing
from .protocol import encode, event
from .transport import LocalTransport


class Runtime:
    def __init__(self, fps: int, ocr: bool, host: str, port: int, token: str, quiet: bool = False):
        self.stop_event = threading.Event()
        self.eye = Eye(EyeConfig(target_fps=fps, ocr=ocr))
        self.token = token
        self.host = host
        self.port = port
        self.latest_state: dict = {}
        self.transport: LocalTransport | None = None
        self.quiet = quiet

    def stop(self, *_args) -> None:
        self.stop_event.set()

    def emit(self, message: dict) -> None:
        message_type = message.get("type")
        if message_type == "eye.keyframe":
            self.latest_state = message
        elif message_type == "eye.delta" and self.latest_state:
            self.latest_state["revision"] = message.get("revision", self.latest_state.get("revision"))
            self.latest_state["frame_hash"] = message.get("frame_hash", self.latest_state.get("frame_hash"))
        elif message_type == "eye.cursor" and self.latest_state:
            self.latest_state["cursor"] = message.get("cursor")

        if self.transport is not None:
            self.transport.publish(message)
        if not self.quiet:
            print(encode(message), flush=True)


def run_connect(
    fps: int,
    ocr: bool,
    host: str,
    port: int,
    pairing_path: str,
    quiet: bool = False,
) -> int:
    pairing = create_pairing()
    save_pairing(pairing_path, pairing)
    runtime = Runtime(fps, ocr, host, port, pairing.token, quiet=quiet)
    signal.signal(signal.SIGINT, runtime.stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, runtime.stop)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        size = (int(monitor["width"]), int(monitor["height"]))

    runtime.transport = LocalTransport(
        runtime.token,
        lambda: runtime.latest_state,
        lambda: size,
    )

    server_thread = threading.Thread(
        target=lambda: asyncio.run(runtime.transport.serve(host, port)),
        daemon=True,
        name="blaxcy-transport",
    )
    server_thread.start()
    if not runtime.transport.wait_ready():
        raise RuntimeError("transport failed to start")

    runtime.emit(event(
        "session.started",
        session=pairing.session_id,
        capabilities=["eye", "mouse", "keyboard", "mcp"],
        transport={"scheme": "ws", "host": host, "port": port},
        pairing=pairing.public(),
        token_fingerprint=fingerprint(runtime.token),
        chatgpt=tool_manifest(),
    ))

    try:
        runtime.eye.run(runtime.emit, runtime.stop_event.is_set)
    finally:
        runtime.emit(event("session.stopped"))

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="blaxcy")
    sub = parser.add_subparsers(dest="command", required=True)

    connect = sub.add_parser("connect", help="start temporary foreground device session")
    connect.add_argument("--fps", type=int, default=60)
    connect.add_argument("--ocr", action="store_true")
    connect.add_argument("--host", default="127.0.0.1")
    connect.add_argument("--port", type=int, default=8765)
    connect.add_argument("--pairing-file", default=".blaxcy/pairing.json")
    connect.add_argument("--quiet", action="store_true")
    connect.add_argument("--no-ocr", action="store_true", help=argparse.SUPPRESS)

    mcp = sub.add_parser("mcp", help="start the ChatGPT MCP connector")
    mcp.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")

    args = parser.parse_args()
    if args.command == "connect":
        raise SystemExit(run_connect(
            args.fps,
            bool(args.ocr and not args.no_ocr),
            args.host,
            args.port,
            args.pairing_file,
            args.quiet,
        ))
    if args.command == "mcp":
        from .mcp_server import main as mcp_main
        import os
        os.environ["BLAXCY_MCP_TRANSPORT"] = args.transport
        mcp_main()
