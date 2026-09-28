from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

API = "https://api.github.com"


class GitHubBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubBridgeConfig:
    repository: str
    issue_number: int
    token: str
    allowed_actor: str
    poll_seconds: float = 1.5


class GitHubBridge:
    """GitHub Issues-comment mailbox for a foreground BLAXCY session."""
    def __init__(self, config: GitHubBridgeConfig,
                 execute_command: Callable[[dict[str, Any]], dict[str, Any]],
                 state_provider: Callable[[], dict[str, Any]]):
        self.config = config
        self.execute_command = execute_command
        self.state_provider = state_provider
        self._last_comment_id = 0

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.config.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "blaxcy-github-bridge",
        }
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read()
                return json.loads(raw.decode()) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise GitHubBridgeError(f"GitHub API {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise GitHubBridgeError(f"GitHub network error: {exc}") from exc

    def _comments(self) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            f"/repos/{self.config.repository}/issues/{self.config.issue_number}/comments"
            "?per_page=100&sort=created&direction=asc",
        )

    def _post(self, body: str) -> None:
        self._request(
            "POST",
            f"/repos/{self.config.repository}/issues/{self.config.issue_number}/comments",
            {"body": body},
        )

    def initialize(self) -> None:
        comments = self._comments()
        self._last_comment_id = max((int(c["id"]) for c in comments), default=0)
        self._post("BLAXCY_SESSION " + json.dumps({
            "status": "connected",
            "capabilities": ["eye", "mouse", "keyboard"],
            "state": self.state_provider(),
        }, separators=(",", ":")))

    def poll_once(self) -> None:
        for comment in self._comments():
            comment_id = int(comment["id"])
            if comment_id <= self._last_comment_id:
                continue
            self._last_comment_id = max(self._last_comment_id, comment_id)

            actor = ((comment.get("user") or {}).get("login") or "").lower()
            if actor != self.config.allowed_actor.lower():
                continue

            body = comment.get("body") or ""
            if not body.startswith("BLAXCY_CMD "):
                continue

            payload: dict[str, Any] = {}
            try:
                payload = json.loads(body[len("BLAXCY_CMD "):])
                command_id = str(payload["id"])
                command = payload["command"]
                if not isinstance(command, dict):
                    raise ValueError("command must be an object")
                result = self.execute_command(command)
                response = {"id": command_id, "ok": True, "result": result}
            except Exception as exc:
                response = {"id": str(payload.get("id", "unknown")), "ok": False, "error": str(exc)}

            self._post("BLAXCY_RESULT " + json.dumps(response, separators=(",", ":")))

    def run(self, stop: Callable[[], bool]) -> None:
        self.initialize()
        while not stop():
            try:
                self.poll_once()
            except GitHubBridgeError as exc:
                print(f"[blaxcy] GitHub bridge: {exc}", flush=True)
            time.sleep(max(0.5, self.config.poll_seconds))


def config_from_env() -> GitHubBridgeConfig:
    repository = os.environ.get("BLAXCY_GITHUB_REPOSITORY", "blaxcy/blaxcy")
    issue = os.environ.get("BLAXCY_GITHUB_ISSUE")
    token = os.environ.get("BLAXCY_GITHUB_TOKEN")
    actor = os.environ.get("BLAXCY_GITHUB_ALLOWED_ACTOR", "blaxcy")
    if not issue or not issue.isdigit():
        raise GitHubBridgeError("BLAXCY_GITHUB_ISSUE must be set to an issue number")
    if not token:
        raise GitHubBridgeError("BLAXCY_GITHUB_TOKEN must be set; never commit it")
    return GitHubBridgeConfig(repository, int(issue), token, actor,
                              float(os.environ.get("BLAXCY_GITHUB_POLL_SECONDS", "1.5")))
