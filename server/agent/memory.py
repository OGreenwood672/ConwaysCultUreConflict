"""Memory dataclass - represents individual memories (observations, reflections, beliefs)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class MemoryType(Enum):
    """Types of memories based on Stanford Generative Agents paper."""
    OBSERVATION = "observation"  # Raw sensory data: "I saw 3 zombies"
    REFLECTION = "reflection"    # Synthesized insight: "Night is dangerous"
    BELIEF = "belief"           # Core conviction: "I cannot trust Bob"
    PLAN = "plan"               # Intended future action: "I will build a wall tomorrow"


@dataclass
class Memory:
    """
    A single memory unit.

    Based on the Stanford Generative Agents architecture where memories have:
    - Content (what happened/was concluded)
    - Importance (how significant, 1-10)
    - Recency (when it happened)
    - Type (observation, reflection, belief)
    - Embedding (for semantic retrieval - computed externally)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent_id: str = ""
    content: str = ""
    memory_type: MemoryType = MemoryType.OBSERVATION
    importance: float = 5.0  # 1-10 scale
    timestamp: datetime = field(default_factory=datetime.now)
    game_day: int = 1
    game_time: str = "dawn"  # dawn, midday, dusk, night

    # Context
    location: Optional[str] = None  # Where this memory was formed
    involved_agents: list[str] = field(default_factory=list)  # Other agents involved
    related_objects: list[str] = field(default_factory=list)  # Objects involved

    # For reflections: what observations led to this
    source_memory_ids: list[str] = field(default_factory=list)

    # Embedding for semantic search (populated by embedding service)
    embedding: Optional[list[float]] = None

    # Retrieval metadata
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0

    def calculate_recency_score(self, current_time: Optional[datetime] = None) -> float:
        """
        Calculate recency score (0-1, higher = more recent).

        Uses exponential decay with half-life of ~1 hour real time.
        """
        if current_time is None:
            current_time = datetime.now()

        age_seconds = (current_time - self.timestamp).total_seconds()
        half_life = 3600  # 1 hour
        return 0.5 ** (age_seconds / half_life)

    def calculate_importance_score(self) -> float:
        """Normalize importance to 0-1 scale."""
        return self.importance / 10.0

    def mark_accessed(self) -> None:
        """Update access metadata when memory is retrieved."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def to_context_string(self) -> str:
        """Convert memory to string for LLM context."""
        type_prefix = {
            MemoryType.OBSERVATION: "[Observed]",
            MemoryType.REFLECTION: "[Reflected]",
            MemoryType.BELIEF: "[Believe]",
            MemoryType.PLAN: "[Plan]",
        }
        prefix = type_prefix.get(self.memory_type, "[Memory]")

        time_str = f"Day {self.game_day}, {self.game_time}"
        if self.location:
            time_str += f" at {self.location}"

        return f"{prefix} ({time_str}): {self.content}"

    def to_dict(self) -> dict:
        """Serialize memory to dictionary for storage."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "game_day": self.game_day,
            "game_time": self.game_time,
            "location": self.location,
            "involved_agents": self.involved_agents,
            "related_objects": self.related_objects,
            "source_memory_ids": self.source_memory_ids,
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """Deserialize memory from dictionary."""
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            importance=data["importance"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            game_day=data["game_day"],
            game_time=data.get("game_time", "dawn"),
            location=data.get("location"),
            involved_agents=data.get("involved_agents", []),
            related_objects=data.get("related_objects", []),
            source_memory_ids=data.get("source_memory_ids", []),
            last_accessed=datetime.fromisoformat(data.get("last_accessed", data["timestamp"])),
            access_count=data.get("access_count", 0),
        )


def create_observation(agent_id: str, content: str, importance: float,
                      game_day: int, game_time: str,
                      location: Optional[str] = None,
                      involved_agents: Optional[list[str]] = None,
                      related_objects: Optional[list[str]] = None) -> Memory:
    """Factory function to create an observation memory."""
    return Memory(
        agent_id=agent_id,
        content=content,
        memory_type=MemoryType.OBSERVATION,
        importance=importance,
        game_day=game_day,
        game_time=game_time,
        location=location,
        involved_agents=involved_agents or [],
        related_objects=related_objects or [],
    )


def create_reflection(agent_id: str, content: str, importance: float,
                     game_day: int, source_memories: list[Memory]) -> Memory:
    """Factory function to create a reflection memory."""
    return Memory(
        agent_id=agent_id,
        content=content,
        memory_type=MemoryType.REFLECTION,
        importance=importance,
        game_day=game_day,
        game_time="reflection",
        source_memory_ids=[m.id for m in source_memories],
    )


def create_belief(agent_id: str, content: str, game_day: int,
                 source_reflections: Optional[list[Memory]] = None) -> Memory:
    """Factory function to create a belief memory."""
    return Memory(
        agent_id=agent_id,
        content=content,
        memory_type=MemoryType.BELIEF,
        importance=9.0,  # Beliefs are high importance
        game_day=game_day,
        game_time="belief",
        source_memory_ids=[m.id for m in (source_reflections or [])],
    )
