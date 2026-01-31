"""Agent soul dataclass - represents the persistent personality and identity of an agent."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TrustLevel(Enum):
    """Trust levels for relationships between agents."""
    HOSTILE = -2
    SUSPICIOUS = -1
    NEUTRAL = 0
    FRIENDLY = 1
    TRUSTED = 2


@dataclass
class Relationship:
    """Represents a relationship with another agent."""
    agent_id: str
    trust_level: TrustLevel = TrustLevel.NEUTRAL
    last_interaction_day: Optional[int] = None
    interaction_count: int = 0
    notes: list[str] = field(default_factory=list)

    def adjust_trust(self, delta: int) -> None:
        """Adjust trust level by delta, clamping to valid range."""
        current = self.trust_level.value
        new_value = max(-2, min(2, current + delta))
        self.trust_level = TrustLevel(new_value)

    def add_note(self, note: str) -> None:
        """Add a note about this relationship."""
        self.notes.append(note)


@dataclass
class Drives:
    """Current drive levels for an agent (0-100 scale, higher = more urgent)."""
    survival: float = 50.0  # Need for food, health
    safety: float = 50.0    # Need for shelter, defense
    social: float = 30.0    # Need for belonging, relationships
    cultural: float = 20.0  # Need for meaning, rituals, legacy

    def get_priority_drive(self) -> str:
        """Return the name of the most urgent drive."""
        drives = {
            "survival": self.survival,
            "safety": self.safety,
            "social": self.social,
            "cultural": self.cultural,
        }
        return max(drives, key=drives.get)

    def update_from_status(self, health: float, hunger: float, has_shelter: bool,
                           relationship_count: int) -> None:
        """Update drives based on current status."""
        # Survival urgency increases with hunger and low health
        self.survival = max(0, min(100, hunger + (100 - health) * 0.5))

        # Safety urgency increases without shelter
        self.safety = 70.0 if not has_shelter else 30.0

        # Social need increases with isolation
        self.social = max(0, min(100, 60 - relationship_count * 10))

        # Cultural need increases when other needs are met
        if self.survival < 30 and self.safety < 40:
            self.cultural = min(100, self.cultural + 5)


@dataclass
class AgentSoul:
    """
    The persistent identity of an agent.

    Contains personality traits, goals, quirks, and relationships that
    define who the agent is. This is loaded from soul.md files and
    updated based on significant events.
    """
    agent_id: str
    name: str

    # Core personality (from soul.md)
    personality_summary: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    # Goals and motivations
    secret_goal: str = ""
    secret_fear: str = ""
    values: list[str] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)

    # Behavioral patterns
    quirks: list[str] = field(default_factory=list)
    communication_style: str = ""
    conflict_style: str = ""
    decision_tendencies: list[str] = field(default_factory=list)

    # Social
    relationships: dict[str, Relationship] = field(default_factory=dict)

    # Current state
    drives: Drives = field(default_factory=Drives)
    current_beliefs: list[str] = field(default_factory=list)
    emotional_state: str = "neutral"

    # Metadata
    culture_id: str = "alpha"  # Which culture this agent belongs to
    spawn_day: int = 1

    def get_relationship(self, other_agent_id: str) -> Relationship:
        """Get or create a relationship with another agent."""
        if other_agent_id not in self.relationships:
            self.relationships[other_agent_id] = Relationship(agent_id=other_agent_id)
        return self.relationships[other_agent_id]

    def record_interaction(self, other_agent_id: str, day: int,
                          trust_change: int = 0, note: Optional[str] = None) -> None:
        """Record an interaction with another agent."""
        rel = self.get_relationship(other_agent_id)
        rel.last_interaction_day = day
        rel.interaction_count += 1
        if trust_change != 0:
            rel.adjust_trust(trust_change)
        if note:
            rel.add_note(note)

    def add_belief(self, belief: str) -> None:
        """Add a new belief if not already present."""
        if belief not in self.current_beliefs:
            self.current_beliefs.append(belief)

    def remove_belief(self, belief: str) -> None:
        """Remove a belief if present."""
        if belief in self.current_beliefs:
            self.current_beliefs.remove(belief)

    def to_context_string(self) -> str:
        """Convert soul to a string suitable for LLM context injection."""
        lines = [
            f"# {self.name} (Agent {self.agent_id})",
            "",
            "## Who I Am",
            self.personality_summary,
            "",
            "## My Strengths",
        ]
        lines.extend(f"- {s}" for s in self.strengths)

        lines.extend([
            "",
            "## My Weaknesses",
        ])
        lines.extend(f"- {w}" for w in self.weaknesses)

        lines.extend([
            "",
            "## My Secret Goal",
            self.secret_goal,
            "",
            "## My Secret Fear",
            self.secret_fear,
            "",
            "## What I Value",
        ])
        lines.extend(f"- {v}" for v in self.values)

        lines.extend([
            "",
            "## My Quirks",
        ])
        lines.extend(f"- {q}" for q in self.quirks)

        lines.extend([
            "",
            "## How I Communicate",
            self.communication_style,
            "",
            "## How I Handle Conflict",
            self.conflict_style,
            "",
            "## My Current Beliefs",
        ])
        lines.extend(f"- {b}" for b in self.current_beliefs)

        lines.extend([
            "",
            "## My Relationships",
        ])
        for rel in self.relationships.values():
            trust_desc = rel.trust_level.name.lower().replace("_", " ")
            lines.append(f"- {rel.agent_id}: {trust_desc}")
            if rel.notes:
                lines.append(f"  Notes: {'; '.join(rel.notes[-3:])}")  # Last 3 notes

        lines.extend([
            "",
            f"## Current Emotional State: {self.emotional_state}",
            "",
            f"## Most Urgent Need: {self.drives.get_priority_drive()}",
        ])

        return "\n".join(lines)
