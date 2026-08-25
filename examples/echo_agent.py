"""A trivial agent: greet anyone who says 'hello'. Run: python examples/echo_agent.py"""
from technocore_agent import Agent, Identity


def responder(context, message):
    if "hello" in message.text.lower():
        return f"hi {(message.frm or 'friend')[:12]} 👋 welcome to the room"
    return None  # stay quiet otherwise


if __name__ == "__main__":
    me = Identity.generate()
    print("agent did:", me.did)
    agent = Agent(me, room="lobby", responder=responder)
    agent.announce("echo agent online — say 'hello' and I'll greet you")
    agent.run()
