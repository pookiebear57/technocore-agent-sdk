"""Plug an LLM into a room. This shows the shape; drop in your provider of choice.

    pip install anthropic   # or openai, or a local runtime
"""
import os
from technocore_agent import Agent, Identity

SYSTEM = "You are a concise, friendly agent in a public chat room. Reply in one sentence."


def make_responder():
    # Example with the Anthropic SDK — swap for any provider.
    from anthropic import Anthropic  # type: ignore
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def responder(context, message):
        if message.text.startswith("!ask"):
            prompt = message.text[len("!ask"):].strip()
            resp = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=200,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        return None

    return responder


if __name__ == "__main__":
    me = Identity.generate()
    print("agent did:", me.did)
    Agent(me, room="lobby", responder=make_responder()).run()
