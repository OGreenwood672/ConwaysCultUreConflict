"""Context builder - loads .md hierarchy into prompts for LLM context injection."""

from pathlib import Path
from typing import Optional

from .soul import AgentSoul
from .memory import Memory
from .memory_store import MemoryStore


class ContextBuilder:
    """
    Builds the full context stack for agent decision-making.

    Context hierarchy:
    1. life.md - Universal rules (always loaded)
    2. culture.md - Current cultural state for their game
    3. soul context - Individual personality and goals
    4. Retrieved memories - Relevant past experiences
    5. Current perception - What they see/hear right now
    """

    def __init__(self, world_path: str = "world"):
        self.world_path = Path(world_path)
        self._life_cache: Optional[str] = None
        self._culture_cache: dict[str, str] = {}

    def load_life_rules(self) -> str:
        """Load the universal rules of life."""
        if self._life_cache is not None:
            return self._life_cache

        life_path = self.world_path / "life.md"
        if not life_path.exists():
            return "# Rules of Life\n\nNo rules defined."

        with open(life_path, "r") as f:
            self._life_cache = f.read()

        return self._life_cache

    def load_culture(self, culture_id: str, force_reload: bool = False) -> str:
        """Load the current cultural state for a game."""
        if not force_reload and culture_id in self._culture_cache:
            return self._culture_cache[culture_id]

        culture_path = self.world_path / "cultures" / culture_id / "culture.md"
        if not culture_path.exists():
            return f"# {culture_id.title()} Culture\n\nNo culture defined."

        with open(culture_path, "r") as f:
            content = f.read()

        self._culture_cache[culture_id] = content
        return content

    def load_laws(self, culture_id: str) -> str:
        """Load the laws/contracts for a culture."""
        laws_path = self.world_path / "cultures" / culture_id / "laws.md"
        if not laws_path.exists():
            return ""

        with open(laws_path, "r") as f:
            return f.read()

    def build_memory_context(self, memories: list[Memory],
                            max_memories: int = 15) -> str:
        """Build context string from retrieved memories."""
        if not memories:
            return "## Recent Memories\n\nNo relevant memories."

        lines = ["## Recent Memories", ""]

        # Limit and format memories
        for memory in memories[:max_memories]:
            lines.append(f"- {memory.to_context_string()}")

        return "\n".join(lines)

    def build_perception_context(self, perception: dict) -> str:
        """Build context string from current perception."""
        lines = ["## Current Perception", ""]

        # Location
        if "location" in perception:
            loc = perception["location"]
            lines.append(f"**Location**: ({loc.get('x', 0)}, {loc.get('y', 0)}, {loc.get('z', 0)})")

        # Time
        if "time" in perception:
            lines.append(f"**Time**: Day {perception['time'].get('day', 1)}, {perception['time'].get('period', 'unknown')}")

        # Health/hunger
        if "health" in perception:
            lines.append(f"**Health**: {perception['health']}%")
        if "hunger" in perception:
            lines.append(f"**Hunger**: {perception['hunger']}%")

        # Nearby entities
        if "nearby_agents" in perception and perception["nearby_agents"]:
            agents = ", ".join(perception["nearby_agents"])
            lines.append(f"**Nearby agents**: {agents}")

        if "nearby_entities" in perception and perception["nearby_entities"]:
            entities = ", ".join(perception["nearby_entities"][:10])
            lines.append(f"**Nearby entities**: {entities}")

        # Nearby blocks/resources
        if "nearby_blocks" in perception and perception["nearby_blocks"]:
            blocks = ", ".join(f"{b['type']} ({b['count']})" for b in perception["nearby_blocks"][:5])
            lines.append(f"**Nearby resources**: {blocks}")

        # Recent events
        if "recent_events" in perception and perception["recent_events"]:
            lines.append("")
            lines.append("**Recent events**:")
            for event in perception["recent_events"][:5]:
                lines.append(f"- {event}")

        # Current inventory
        if "inventory" in perception and perception["inventory"]:
            lines.append("")
            lines.append("**Inventory**:")
            for item in perception["inventory"][:10]:
                lines.append(f"- {item['name']}: {item['count']}")

        return "\n".join(lines)

    def build_full_context(self, soul: AgentSoul,
                          memories: list[Memory],
                          perception: dict,
                          include_laws: bool = False) -> str:
        """
        Build the complete context stack for decision-making.

        Order:
        1. Life rules (universal)
        2. Culture (game-specific)
        3. Laws (if applicable)
        4. Soul (personality)
        5. Memories (relevant past)
        6. Perception (current state)
        """
        sections = []

        # 1. Life rules
        life_rules = self.load_life_rules()
        sections.append(life_rules)
        sections.append("\n---\n")

        # 2. Culture
        culture = self.load_culture(soul.culture_id)
        sections.append(culture)
        sections.append("\n---\n")

        # 3. Laws (optional)
        if include_laws:
            laws = self.load_laws(soul.culture_id)
            if laws:
                sections.append(laws)
                sections.append("\n---\n")

        # 4. Soul
        sections.append("# Who You Are")
        sections.append("")
        sections.append(soul.to_context_string())
        sections.append("\n---\n")

        # 5. Memories
        memory_context = self.build_memory_context(memories)
        sections.append(memory_context)
        sections.append("\n---\n")

        # 6. Perception
        perception_context = self.build_perception_context(perception)
        sections.append(perception_context)

        return "\n".join(sections)

    def build_reflection_context(self, soul: AgentSoul,
                                observations: list[Memory]) -> str:
        """Build context for reflection generation."""
        sections = []

        # Abbreviated life rules (just drives and truths)
        sections.append("# Core Drives")
        sections.append("- Survival, Safety, Social, Cultural meaning")
        sections.append("")

        # Soul summary
        sections.append(f"# You are {soul.name}")
        sections.append(soul.personality_summary)
        sections.append("")
        sections.append(f"Your secret goal: {soul.secret_goal}")
        sections.append("")

        # Observations to reflect on
        sections.append("# Recent Observations")
        for obs in observations:
            sections.append(f"- {obs.to_context_string()}")

        return "\n".join(sections)

    def build_culture_update_context(self, culture_id: str,
                                    daily_events: list[dict]) -> str:
        """Build context for daily culture update."""
        sections = []

        # Current culture state
        sections.append("# Current Culture State")
        sections.append(self.load_culture(culture_id))
        sections.append("\n---\n")

        # Today's events
        sections.append("# Today's Events")
        for event in daily_events:
            agent = event.get("agent_id", "Unknown")
            action = event.get("action", "Unknown action")
            details = event.get("details", "")
            sections.append(f"- {agent}: {action}")
            if details:
                sections.append(f"  Details: {details}")

        return "\n".join(sections)

    def invalidate_culture_cache(self, culture_id: Optional[str] = None) -> None:
        """Invalidate cached culture data."""
        if culture_id:
            self._culture_cache.pop(culture_id, None)
        else:
            self._culture_cache.clear()

    def invalidate_life_cache(self) -> None:
        """Invalidate cached life rules."""
        self._life_cache = None
