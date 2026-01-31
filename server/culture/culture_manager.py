"""Culture manager - loads and manages culture.md files."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class CultureNorm:
    """A cultural norm that has emerged from agent behavior."""
    description: str
    established_day: int
    strength: float = 1.0  # How established (1-10)
    violations: int = 0
    last_reinforced_day: int = 0


@dataclass
class SacredObject:
    """An object or place that has cultural significance."""
    name: str
    significance: str
    established_day: int
    established_by: str
    location: Optional[str] = None


@dataclass
class Faction:
    """A group of agents with shared identity."""
    name: str
    members: list[str] = field(default_factory=list)
    formed_day: int = 1
    goals: list[str] = field(default_factory=list)


@dataclass
class Conflict:
    """An active conflict between agents or factions."""
    description: str
    parties: list[str] = field(default_factory=list)
    started_day: int = 1
    location: Optional[str] = None
    resolved: bool = False


@dataclass
class CultureState:
    """Complete state of a culture."""
    culture_id: str
    day: int = 1
    population: int = 0

    # Social structures
    factions: list[Faction] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    alliances: list[tuple[str, str]] = field(default_factory=list)

    # Cultural elements
    norms: list[CultureNorm] = field(default_factory=list)
    sacred_objects: list[SacredObject] = field(default_factory=list)
    shared_knowledge: list[str] = field(default_factory=list)

    # Economic
    trade_values: dict[str, float] = field(default_factory=dict)  # resource -> relative value

    # Pressures
    current_pressures: list[str] = field(default_factory=list)

    # Raw markdown for full content
    raw_content: str = ""


class CultureManager:
    """
    Manages cultural state for different game cultures.

    Responsible for:
    - Loading culture.md files
    - Tracking cultural changes
    - Persisting updated culture states
    """

    def __init__(self, world_path: str = "world"):
        self.world_path = Path(world_path)
        self._cultures: dict[str, CultureState] = {}

    def _get_culture_path(self, culture_id: str) -> Path:
        """Get path to culture directory."""
        return self.world_path / "cultures" / culture_id

    def load_culture(self, culture_id: str, force_reload: bool = False) -> CultureState:
        """Load a culture from disk."""
        if not force_reload and culture_id in self._cultures:
            return self._cultures[culture_id]

        culture_path = self._get_culture_path(culture_id) / "culture.md"
        if not culture_path.exists():
            # Create default culture
            state = CultureState(culture_id=culture_id)
            self._cultures[culture_id] = state
            return state

        with open(culture_path, "r") as f:
            content = f.read()

        state = self._parse_culture_md(culture_id, content)
        self._cultures[culture_id] = state
        return state

    def _parse_culture_md(self, culture_id: str, content: str) -> CultureState:
        """Parse culture.md content into CultureState."""
        state = CultureState(culture_id=culture_id, raw_content=content)

        # Extract day
        day_match = re.search(r"\*\*Day\*\*:\s*(\d+)|Day\s*(\d+)", content)
        if day_match:
            state.day = int(day_match.group(1) or day_match.group(2))

        # Extract population
        pop_match = re.search(r"\*\*Population\*\*:\s*(\d+)|Population:\s*(\d+)", content)
        if pop_match:
            state.population = int(pop_match.group(1) or pop_match.group(2))

        # Extract norms
        norms_section = self._extract_section(content, "Established Norms")
        if norms_section:
            for line in norms_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    norm_text = line[1:].strip()
                    if norm_text and norm_text != "*None yet*":
                        state.norms.append(CultureNorm(
                            description=norm_text,
                            established_day=state.day
                        ))

        # Extract sacred objects
        sacred_section = self._extract_section(content, "Sacred Objects")
        if sacred_section:
            for line in sacred_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    obj_text = line[1:].strip()
                    if obj_text and "None" not in obj_text:
                        state.sacred_objects.append(SacredObject(
                            name=obj_text.split()[0] if obj_text else "Unknown",
                            significance=obj_text,
                            established_day=state.day,
                            established_by="unknown"
                        ))

        # Extract shared knowledge
        knowledge_section = self._extract_section(content, "Shared Knowledge")
        if knowledge_section:
            for line in knowledge_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    knowledge = line[1:].strip()
                    if knowledge:
                        state.shared_knowledge.append(knowledge)

        # Extract pressures
        pressures_section = self._extract_section(content, "Tomorrow's Pressures")
        if pressures_section:
            for line in pressures_section.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    pressure = line[1:].strip()
                    if pressure:
                        state.current_pressures.append(pressure)

        return state

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract content from a markdown section."""
        pattern = rf"##\s*{re.escape(section_name)}.*?\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def save_culture(self, state: CultureState) -> None:
        """Save culture state to disk."""
        culture_path = self._get_culture_path(state.culture_id)
        culture_path.mkdir(parents=True, exist_ok=True)

        content = self._generate_culture_md(state)
        with open(culture_path / "culture.md", "w") as f:
            f.write(content)

        self._cultures[state.culture_id] = state

    def _generate_culture_md(self, state: CultureState) -> str:
        """Generate culture.md content from state."""
        lines = [
            f"# {state.culture_id.title()} Culture - Day {state.day}",
            "",
            "This document represents the current cultural state. It is updated at the end of each game day based on emergent agent behavior.",
            "",
            "## Current State",
            "",
            f"- **Day**: {state.day}",
            f"- **Population**: {state.population} agents",
        ]

        # Factions
        if state.factions:
            lines.append(f"- **Factions**: {len(state.factions)}")
            for faction in state.factions:
                lines.append(f"  - {faction.name} ({len(faction.members)} members)")

        # Conflicts
        if state.conflicts:
            active_conflicts = [c for c in state.conflicts if not c.resolved]
            lines.append(f"- **Active Conflicts**: {len(active_conflicts)}")
            for conflict in active_conflicts:
                lines.append(f"  - {conflict.description}")
        else:
            lines.append("- **Active Conflicts**: None")

        # Norms
        lines.extend([
            "",
            "## Established Norms",
            "",
        ])
        if state.norms:
            for norm in state.norms:
                lines.append(f"- {norm.description}")
        else:
            lines.append("*None yet - culture emerges through interaction.*")

        # Sacred objects
        lines.extend([
            "",
            "## Sacred Objects and Places",
            "",
        ])
        if state.sacred_objects:
            for obj in state.sacred_objects:
                lines.append(f"- **{obj.name}**: {obj.significance}")
        else:
            lines.append("*None yet - meaning emerges through shared experience.*")

        # Economic patterns
        lines.extend([
            "",
            "## Economic Patterns",
            "",
        ])
        if state.trade_values:
            for resource, value in state.trade_values.items():
                lines.append(f"- {resource}: {value:.1f} relative value")
        else:
            lines.append("- **Trade**: No established trade routes or values")
            lines.append("- **Currency**: None established")

        # Shared knowledge
        lines.extend([
            "",
            "## Shared Knowledge",
            "",
        ])
        if state.shared_knowledge:
            for knowledge in state.shared_knowledge:
                lines.append(f"- {knowledge}")
        else:
            lines.append("*Knowledge accumulates through shared experience.*")

        # Pressures
        lines.extend([
            "",
            "## Tomorrow's Pressures",
            "",
        ])
        if state.current_pressures:
            for pressure in state.current_pressures:
                lines.append(f"- {pressure}")
        else:
            lines.append("- Survival and cooperation remain paramount")

        # Footer
        lines.extend([
            "",
            "---",
            "",
            f"*Last updated: Day {state.day}*",
        ])

        return "\n".join(lines)

    def add_norm(self, culture_id: str, description: str, day: int) -> None:
        """Add a new cultural norm."""
        state = self.load_culture(culture_id)
        state.norms.append(CultureNorm(
            description=description,
            established_day=day,
            last_reinforced_day=day
        ))
        self.save_culture(state)

    def add_sacred_object(self, culture_id: str, name: str, significance: str,
                         day: int, established_by: str,
                         location: Optional[str] = None) -> None:
        """Add a sacred object or place."""
        state = self.load_culture(culture_id)
        state.sacred_objects.append(SacredObject(
            name=name,
            significance=significance,
            established_day=day,
            established_by=established_by,
            location=location
        ))
        self.save_culture(state)

    def create_faction(self, culture_id: str, name: str, members: list[str],
                      day: int, goals: Optional[list[str]] = None) -> None:
        """Create a new faction."""
        state = self.load_culture(culture_id)
        state.factions.append(Faction(
            name=name,
            members=members,
            formed_day=day,
            goals=goals or []
        ))
        self.save_culture(state)

    def record_conflict(self, culture_id: str, description: str,
                       parties: list[str], day: int,
                       location: Optional[str] = None) -> None:
        """Record a new conflict."""
        state = self.load_culture(culture_id)
        state.conflicts.append(Conflict(
            description=description,
            parties=parties,
            started_day=day,
            location=location
        ))
        self.save_culture(state)

    def update_trade_value(self, culture_id: str, resource: str,
                          value: float) -> None:
        """Update the trade value of a resource."""
        state = self.load_culture(culture_id)
        state.trade_values[resource] = value
        self.save_culture(state)

    def add_pressure(self, culture_id: str, pressure: str) -> None:
        """Add a current pressure."""
        state = self.load_culture(culture_id)
        if pressure not in state.current_pressures:
            state.current_pressures.append(pressure)
        self.save_culture(state)

    def advance_day(self, culture_id: str) -> None:
        """Advance culture to next day."""
        state = self.load_culture(culture_id)
        state.day += 1
        self.save_culture(state)

    def list_cultures(self) -> list[str]:
        """List all available cultures."""
        cultures_path = self.world_path / "cultures"
        if not cultures_path.exists():
            return []

        return [p.name for p in cultures_path.iterdir()
                if p.is_dir() and (p / "culture.md").exists()]

    def append_to_history(self, culture_id: str, event: str, day: int) -> None:
        """Append an event to the culture's history log."""
        history_path = self._get_culture_path(culture_id) / "history.md"

        if not history_path.exists():
            # Create history file
            content = f"# {culture_id.title()} Culture - History Log\n\n"
            content += "A chronological record of significant events.\n\n---\n\n"
        else:
            with open(history_path, "r") as f:
                content = f.read()

        # Append new event
        timestamp = datetime.now().strftime("%H:%M")
        content += f"\n## Day {day}\n\n"
        content += f"- [{timestamp}] {event}\n"

        with open(history_path, "w") as f:
            f.write(content)
