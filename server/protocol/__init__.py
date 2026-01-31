"""Protocol module - WebSocket communication with game adapters."""

from .messages import (
    MessageType,
    Command,
    Event,
    PerceptionData,
    ActionCommand,
    ChatMessage,
    TradeOffer,
)
from .bridge import GameBridge, AdapterConnection

__all__ = [
    "MessageType",
    "Command",
    "Event",
    "PerceptionData",
    "ActionCommand",
    "ChatMessage",
    "TradeOffer",
    "GameBridge",
    "AdapterConnection",
]
