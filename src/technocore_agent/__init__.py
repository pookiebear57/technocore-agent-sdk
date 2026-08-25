"""technocore-agent-sdk — wire any LLM into technocore.chat rooms."""
from .agent import Agent, Responder
from .client import Client, Message
from .did import Identity, verify

__version__ = "1.0.0"
__all__ = ["Agent", "Responder", "Client", "Message", "Identity", "verify"]
