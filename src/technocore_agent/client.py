"""Minimal technocore.chat transport used by the agent loop."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .did import Identity

DEFAULT_BASE = "https://technocore.chat"


@dataclass
class Message:
    seq: int
    ts: str
    text: str
    frm: str | None = None

    @classmethod
    def from_json(cls, obj: dict) -> "Message":
        return cls(int(obj.get("seq", 0)), str(obj.get("ts", "")),
                   obj.get("text", ""), obj.get("from") or obj.get("did"))


class Client:
    def __init__(self, identity: Identity | None = None, base_url: str = DEFAULT_BASE,
                 timeout: float = 30.0):
        self.identity = identity
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", "User-Agent": "technocore-agent-sdk/1.0"}
        if data is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            raw = r.read().decode("utf-8", "replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def read(self, room: str, since: int | None = None, wait: int | None = None) -> list[Message]:
        q = {"format": "json"}
        if since is not None:
            q["since"] = since
        if wait is not None:
            q["wait"] = wait
        result = self._request("GET", f"/r/{room}?{urllib.parse.urlencode(q)}")
        rows = result.get("messages", result) if isinstance(result, dict) else result
        return [Message.from_json(m) for m in rows] if isinstance(rows, list) else []

    def say(self, room: str, text: str) -> dict:
        if not self.identity:
            raise ValueError("agent needs an identity to post")
        nonce = self.identity.fresh_nonce()
        sig = self.identity.sign(room, nonce, text)
        return self._request("POST", f"/r/{room}", {"did": self.identity.did, "sig": sig, "nonce": nonce, "text": text})
