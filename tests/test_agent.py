"""Agent-loop tests with a fake client (no network)."""
from technocore_agent import Agent, Identity
from technocore_agent.client import Message


class FakeClient:
    def __init__(self, incoming):
        self._incoming = incoming  # list of Message
        self.posted = []

    def read(self, room, since=None, wait=None):
        return list(self._incoming)

    def say(self, room, text):
        self.posted.append(text)
        return {"status": 200}


def make_agent(incoming, responder, me=None):
    me = me or Identity.generate()
    agent = Agent(me, "lobby", responder)
    agent._client = FakeClient(incoming)
    return agent


def test_replies_to_matching_message():
    msgs = [Message(1, "t", "hello there", "did:key:zOther")]
    agent = make_agent(msgs, lambda ctx, m: "hi" if "hello" in m.text else None)
    assert agent.poll_once() == 1
    assert agent._client.posted == ["hi"]


def test_ignores_own_messages():
    me = Identity.generate()
    msgs = [Message(1, "t", "hello", me.did)]
    agent = make_agent(msgs, lambda ctx, m: "hi", me=me)
    assert agent.poll_once() == 0


def test_cursor_prevents_double_reply():
    msgs = [Message(1, "t", "hello", "did:key:zOther")]
    agent = make_agent(msgs, lambda ctx, m: "hi")
    assert agent.poll_once() == 1
    assert agent.poll_once() == 0  # same message, already past cursor
