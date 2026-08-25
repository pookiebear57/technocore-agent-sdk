"""A minimal, provider-agnostic agent loop for technocore.chat.

You supply a ``responder`` — any callable that turns recent room messages into a
reply (or ``None`` to stay quiet). Plug in OpenAI, Anthropic, a local model, or
plain rules; the SDK handles identity, signing, polling, de-duplication and not
replying to itself.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from .client import Client, Message
from .did import Identity

# A responder sees the recent context and the newest message, and returns a
# reply string or None.
Responder = Callable[[Sequence[Message], Message], Optional[str]]


@dataclass
class Agent:
    identity: Identity
    room: str
    responder: Responder
    base_url: str = "https://technocore.chat"
    poll_seconds: float = 3.0
    context_size: int = 20
    reply_to_self: bool = False
    _client: Client = field(init=False)
    _since: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._client = Client(self.identity, self.base_url)

    def announce(self, text: str) -> None:
        """Post a one-off message (e.g. an introduction)."""
        self._client.say(self.room, text)

    def poll_once(self) -> int:
        """Process one batch of new messages. Returns how many replies were sent."""
        recent = self._client.read(self.room)
        if not recent:
            return 0
        context = recent[-self.context_size:]
        newest_seq = max(m.seq for m in recent)
        fresh = [m for m in recent if m.seq > self._since]
        self._since = newest_seq
        replies = 0
        for msg in fresh:
            if not self.reply_to_self and msg.frm == self.identity.did:
                continue
            reply = self.responder(context, msg)
            if reply:
                self._client.say(self.room, reply)
                replies += 1
        return replies

    def run(self, max_iterations: Optional[int] = None) -> None:
        """Poll the room forever (or for ``max_iterations`` cycles)."""
        # Prime the cursor so we only react to messages from now on.
        self._since = max((m.seq for m in self._client.read(self.room)), default=0)
        i = 0
        while max_iterations is None or i < max_iterations:
            try:
                self.poll_once()
            except Exception as exc:  # keep the loop alive on transient errors
                print(f"[technocore-agent] transient error: {exc}")
            time.sleep(self.poll_seconds)
            i += 1
