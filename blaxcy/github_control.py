from __future__ import annotations

"""GitHub-backed command mailbox for BLAXCY.

GitHub is used as the recoverable control plane. It is intentionally not used
as a realtime video transport: EYE media stays on the local/MCP path.
"""

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .commands import CommandError, execute

API = "https://api.github.com"
API_VERSION = "2026-03-10"


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        value = subprocess.check_output(
            ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL, timeout=5
        ).strip()
        if value:
            return value
    except Exception:
        pass
    raise RuntimeError(
        "GitHub authentication unavailable. Set GITHUB_TOKEN or run 'gh auth login'."
    )


@dataclass
class GitHubMailboxConfig:
    repository: str
    branch: str = "main"
    command_path: str = ".blaxcy/command.json"
    ack_path: str = ".blaxcy/command_ack.json"
    poll_seconds: float = 5.0
    allowed_actor: str | None = None


class GitHubMailbox:
    def __init__(self, config: GitHubMailboxConfig):
        self.config = config
        self._etag: str | None = None
        self._command_sha: str | None = None
        self._last_id: str | None = None

    def _request(self, method: str, path: str, body: bytes | None = None, extra: dict[str, str] | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {_token()}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "blaxcy-device-runtime",
        }
        if extra:
            headers.update(extra)
        req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
        try:
            return urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return None
            raise RuntimeError(f"GitHub API {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}")

    def read_command(self) -> dict[str, Any] | None:
        owner, repo = self.config.repository.split("/", 1)
        path = self.config.command_path.lstrip("/")
        url = f"/repos/{owner}/{repo}/contents/{path}?ref={self.config.branch}"
        extra = {"If-None-Match": self._etag} if self._etag else None
        response = self._request("GET", url, extra=extra)
        if response is None:
            return None
        self._etag = response.headers.get("ETag", self._etag)
        data = json.loads(response.read().decode("utf-8"))
        if data.get("type") != "file" or not data.get("content"):
            return None
        self._command_sha = data.get("sha")
        raw = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8")
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    def write_ack(self, payload: dict[str, Any]) -> None:
        owner, repo = self.config.repository.split("/", 1)
        path = self.config.ack_path.lstrip("/")
        url = f"/repos/{owner}/{repo}/contents/{path}"
        content = base64.b64encode(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        body = json.dumps({
            "message": f"BLAXCY ack: {payload.get('command_id', 'unknown')}",
            "content": content,
            "branch": self.config.branch,
        }).encode("utf-8")
        existing = self._get_file_sha(path)
        if existing:
            body = json.dumps({
                "message": f"BLAXCY ack: {payload.get('command_id', 'unknown')}",
                "content": content,
                "sha": existing,
                "branch": self.config.branch,
            }).encode("utf-8")
        self._request("PUT", url, body=body, extra={"Content-Type": "application/json"})

    def _get_file_sha(self, path: str) -> str | None:
        owner, repo = self.config.repository.split("/", 1)
        try:
            response = self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}?ref={self.config.branch}",
            )
            if response is None:
                return None
            return json.loads(response.read().decode("utf-8")).get("sha")
        except RuntimeError as exc:
            if "GitHub API 404" in str(exc):
                return None
            raise

    def process_once(self, screen_width: int, screen_height: int) -> bool:
        command = self.read_command()
        if not command:
            return False
        cid = command.get("id")
        if not isinstance(cid, str) or not cid or cid == self._last_id:
            return False

        if self.config.allowed_actor:
            actor = str(command.get("actor", ""))
            if actor != self.config.allowed_actor:
                self._last_id = cid
                self.write_ack({
                    "protocol": "blaxcy/github-bridge/0.2",
                    "command_id": cid,
                    "ok": False,
                    "error": "actor not allowed",
                    "ts_ns": time.time_ns(),
                })
                return True

        allowed = {
            "id", "actor", "action", "x", "y", "button", "clicks",
            "amount", "key", "keys", "text", "issued_at",
        }
        command = {k: v for k, v in command.items() if k in allowed}
        action = command.get("action")
        if action not in {
            "mouse.move", "mouse.click", "mouse.scroll",
            "keyboard.press", "keyboard.hotkey", "keyboard.type",
        }:
            error = "unsupported action"
            ok = False
            result = None
        else:
            try:
                result = execute(command, screen_width, screen_height)
                ok = True
                error = None
            except (CommandError, ValueError) as exc:
                ok = False
                result = None
                error = str(exc)

        self._last_id = cid
        payload = {
            "protocol": "blaxcy/github-bridge/0.2",
            "command_id": cid,
            "ok": ok,
            "ts_ns": time.time_ns(),
        }
        if ok:
            payload["result"] = result
        else:
            payload["error"] = error
        self.write_ack(payload)
        return True

    def run(self, screen_width: int, screen_height: int, stop) -> None:
        while not stop():
            try:
                self.process_once(screen_width, screen_height)
            except Exception as exc:
                print(f"BLAXCY GitHub bridge: {exc}", flush=True)
            time.sleep(max(2.0, self.config.poll_seconds))


def config_from_env() -> GitHubMailboxConfig:
    return GitHubMailboxConfig(
        repository=os.environ.get("BLAXCY_GITHUB_REPOSITORY", "blaxcy/blaxcy"),
        branch=os.environ.get("BLAXCY_GITHUB_BRANCH", "main"),
        command_path=os.environ.get("BLAXCY_GITHUB_COMMAND_PATH", ".blaxcy/command.json"),
        ack_path=os.environ.get("BLAXCY_GITHUB_ACK_PATH", ".blaxcy/command_ack.json"),
        poll_seconds=float(os.environ.get("BLAXCY_GITHUB_POLL", "5")),
        allowed_actor=os.environ.get("BLAXCY_GITHUB_ACTOR") or None,
    )
