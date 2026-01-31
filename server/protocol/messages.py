"""Message types for protocol between server and game adapters."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Any
import json


class MessageType(Enum):
    """Types of messages in the protocol."""
    # Server -> Adapter (Commands)
    MOVE = "move"
    GATHER = "gather"
    BUILD = "build"
    ATTACK = "attack"
    CHAT = "chat"
    TRADE_OFFER = "trade_offer"
    TRADE_RESPOND = "trade_respond"
    CRAFT = "craft"
    EXAMINE = "examine"

    # Adapter -> Server (Events)
    PERCEPTION = "perception"
    CHAT_RECEIVED = "chat_received"
    ACTION_COMPLETE = "action_complete"
    ACTION_FAILED = "action_failed"
    COMBAT = "combat"
    TRADE_INCOMING = "trade_incoming"
    TRADE_COMPLETE = "trade_complete"
    DEATH = "death"
    DISCOVERY = "discovery"
    TIME_UPDATE = "time_update"

    # Control messages
    REGISTER = "register"
    REGISTER_ACK = "register_ack"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class Message:
    """Base message class."""
    type: MessageType
    agent_id: str
    timestamp: float = 0.0
    payload: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "type": self.type.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
        })

    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Deserialize from JSON string."""
        obj = json.loads(data)
        return cls(
            type=MessageType(obj["type"]),
            agent_id=obj["agent_id"],
            timestamp=obj.get("timestamp", 0.0),
            payload=obj.get("payload", {}),
        )


# Command Messages (Server -> Adapter)

@dataclass
class Command:
    """Base command from server to adapter."""
    type: MessageType
    agent_id: str
    timestamp: float = 0.0

    def to_message(self) -> Message:
        """Convert to generic message."""
        return Message(
            type=self.type,
            agent_id=self.agent_id,
            timestamp=self.timestamp,
            payload=self._get_payload(),
        )

    def _get_payload(self) -> dict:
        """Override in subclasses to provide payload."""
        return {}


@dataclass
class ActionCommand(Command):
    """Command to perform an action."""
    action: str = ""
    target: Optional[str] = None
    parameters: dict = field(default_factory=dict)

    def _get_payload(self) -> dict:
        return {
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
        }


@dataclass
class MoveCommand(Command):
    """Command to move the agent."""
    type: MessageType = MessageType.MOVE
    direction: str = ""  # north, south, east, west, or coordinates
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    def _get_payload(self) -> dict:
        payload = {"direction": self.direction}
        if self.x is not None:
            payload["x"] = self.x
            payload["y"] = self.y
            payload["z"] = self.z
        return payload


@dataclass
class GatherCommand(Command):
    """Command to gather a resource."""
    type: MessageType = MessageType.GATHER
    resource_type: str = ""
    location: Optional[dict] = None

    def _get_payload(self) -> dict:
        payload = {"resource_type": self.resource_type}
        if self.location:
            payload["location"] = self.location
        return payload


@dataclass
class ChatMessage(Command):
    """Command to send a chat message."""
    type: MessageType = MessageType.CHAT
    message: str = ""
    target: Optional[str] = None  # None = broadcast, string = whisper

    def _get_payload(self) -> dict:
        return {
            "message": self.message,
            "target": self.target,
        }


@dataclass
class TradeOffer(Command):
    """Command to offer a trade."""
    type: MessageType = MessageType.TRADE_OFFER
    target_agent: str = ""
    offering: list[dict] = field(default_factory=list)  # [{item, count}]
    requesting: list[dict] = field(default_factory=list)

    def _get_payload(self) -> dict:
        return {
            "target_agent": self.target_agent,
            "offering": self.offering,
            "requesting": self.requesting,
        }


@dataclass
class TradeRespond(Command):
    """Command to respond to a trade offer."""
    type: MessageType = MessageType.TRADE_RESPOND
    trade_id: str = ""
    accept: bool = False

    def _get_payload(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "accept": self.accept,
        }


@dataclass
class AttackCommand(Command):
    """Command to attack a target."""
    type: MessageType = MessageType.ATTACK
    target: str = ""  # Entity ID or agent ID

    def _get_payload(self) -> dict:
        return {"target": self.target}


@dataclass
class BuildCommand(Command):
    """Command to build something."""
    type: MessageType = MessageType.BUILD
    structure_type: str = ""
    location: Optional[dict] = None
    materials: list[str] = field(default_factory=list)

    def _get_payload(self) -> dict:
        return {
            "structure_type": self.structure_type,
            "location": self.location,
            "materials": self.materials,
        }


# Event Messages (Adapter -> Server)

@dataclass
class Event:
    """Base event from adapter to server."""
    type: MessageType
    agent_id: str
    timestamp: float = 0.0

    @classmethod
    def from_message(cls, message: Message) -> "Event":
        """Create event from generic message."""
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
        )


@dataclass
class PerceptionData:
    """Perception data from the game world."""
    # Position
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    # Agent state
    health: float = 100.0
    hunger: float = 0.0
    has_shelter: bool = False

    # Environment
    biome: str = "plains"
    light_level: int = 15
    weather: str = "clear"

    # Time
    game_day: int = 1
    game_time: str = "dawn"  # dawn, midday, dusk, night
    is_night: bool = False

    # Nearby things
    nearby_agents: list[str] = field(default_factory=list)
    nearby_entities: list[str] = field(default_factory=list)
    nearby_blocks: list[dict] = field(default_factory=list)  # [{type, count, distance}]

    # Recent events
    recent_events: list[str] = field(default_factory=list)

    # Inventory
    inventory: list[dict] = field(default_factory=list)  # [{name, count}]

    def to_dict(self) -> dict:
        """Convert to dictionary for context building."""
        return {
            "location": {"x": self.x, "y": self.y, "z": self.z},
            "health": self.health,
            "hunger": self.hunger,
            "has_shelter": self.has_shelter,
            "time": {"day": self.game_day, "period": self.game_time},
            "is_night": self.is_night,
            "biome": self.biome,
            "weather": self.weather,
            "nearby_agents": self.nearby_agents,
            "nearby_entities": self.nearby_entities,
            "nearby_blocks": self.nearby_blocks,
            "recent_events": self.recent_events,
            "inventory": self.inventory,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PerceptionData":
        """Create from dictionary."""
        loc = data.get("location", {})
        time = data.get("time", {})

        return cls(
            x=loc.get("x", 0),
            y=loc.get("y", 0),
            z=loc.get("z", 0),
            health=data.get("health", 100),
            hunger=data.get("hunger", 0),
            has_shelter=data.get("has_shelter", False),
            biome=data.get("biome", "plains"),
            light_level=data.get("light_level", 15),
            weather=data.get("weather", "clear"),
            game_day=time.get("day", 1),
            game_time=time.get("period", "dawn"),
            is_night=data.get("is_night", False),
            nearby_agents=data.get("nearby_agents", []),
            nearby_entities=data.get("nearby_entities", []),
            nearby_blocks=data.get("nearby_blocks", []),
            recent_events=data.get("recent_events", []),
            inventory=data.get("inventory", []),
        )


@dataclass
class PerceptionEvent(Event):
    """Perception update from adapter."""
    type: MessageType = MessageType.PERCEPTION
    perception: PerceptionData = field(default_factory=PerceptionData)

    @classmethod
    def from_message(cls, message: Message) -> "PerceptionEvent":
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
            perception=PerceptionData.from_dict(message.payload),
        )


@dataclass
class ChatReceivedEvent(Event):
    """Chat message received from another agent."""
    type: MessageType = MessageType.CHAT_RECEIVED
    sender: str = ""
    message: str = ""
    is_whisper: bool = False

    @classmethod
    def from_message(cls, message: Message) -> "ChatReceivedEvent":
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
            sender=message.payload.get("sender", ""),
            message=message.payload.get("message", ""),
            is_whisper=message.payload.get("is_whisper", False),
        )


@dataclass
class ActionCompleteEvent(Event):
    """Action completed successfully."""
    type: MessageType = MessageType.ACTION_COMPLETE
    action: str = ""
    result: dict = field(default_factory=dict)

    @classmethod
    def from_message(cls, message: Message) -> "ActionCompleteEvent":
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
            action=message.payload.get("action", ""),
            result=message.payload.get("result", {}),
        )


@dataclass
class CombatEvent(Event):
    """Combat occurred."""
    type: MessageType = MessageType.COMBAT
    opponent: str = ""
    damage_dealt: float = 0.0
    damage_received: float = 0.0
    outcome: str = ""  # ongoing, won, lost, fled

    @classmethod
    def from_message(cls, message: Message) -> "CombatEvent":
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
            opponent=message.payload.get("opponent", ""),
            damage_dealt=message.payload.get("damage_dealt", 0),
            damage_received=message.payload.get("damage_received", 0),
            outcome=message.payload.get("outcome", "ongoing"),
        )


@dataclass
class TimeUpdateEvent(Event):
    """Game time updated."""
    type: MessageType = MessageType.TIME_UPDATE
    day: int = 1
    period: str = "dawn"
    is_night: bool = False

    @classmethod
    def from_message(cls, message: Message) -> "TimeUpdateEvent":
        return cls(
            type=message.type,
            agent_id=message.agent_id,
            timestamp=message.timestamp,
            day=message.payload.get("day", 1),
            period=message.payload.get("period", "dawn"),
            is_night=message.payload.get("is_night", False),
        )


def parse_event(message: Message) -> Event:
    """Parse a message into the appropriate event type."""
    event_classes = {
        MessageType.PERCEPTION: PerceptionEvent,
        MessageType.CHAT_RECEIVED: ChatReceivedEvent,
        MessageType.ACTION_COMPLETE: ActionCompleteEvent,
        MessageType.COMBAT: CombatEvent,
        MessageType.TIME_UPDATE: TimeUpdateEvent,
    }

    event_class = event_classes.get(message.type, Event)
    return event_class.from_message(message)
