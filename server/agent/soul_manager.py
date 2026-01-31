"""Soul manager - CRUD operations and persistence for agent souls."""

import os
import re
from pathlib import Path
from typing import Optional

from .soul import AgentSoul, Relationship, TrustLevel, Drives


class SoulManager:
    """
    Manages loading, saving, and updating agent souls.

    Souls are stored as markdown files in world/agents/<agent_id>/soul.md
    Status is stored in world/agents/<agent_id>/status.md
    """

    def __init__(self, world_path: str = "world"):
        self.world_path = Path(world_path)
        self.agents_path = self.world_path / "agents"
        self._cache: dict[str, AgentSoul] = {}

    def _parse_markdown_section(self, content: str, section_name: str) -> list[str]:
        """Extract bullet points from a markdown section."""
        pattern = rf"##\s*{re.escape(section_name)}.*?\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return []

        section_content = match.group(1)
        items = []
        for line in section_content.strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                items.append(line[2:].strip())
            elif line.startswith("* "):
                items.append(line[2:].strip())
        return items

    def _parse_markdown_text(self, content: str, section_name: str) -> str:
        """Extract text content from a markdown section."""
        pattern = rf"##\s*{re.escape(section_name)}.*?\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return ""

        section_content = match.group(1).strip()
        # Remove bullet points and join non-empty lines
        lines = []
        for line in section_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("-") and not line.startswith("*"):
                lines.append(line)
        return " ".join(lines)

    def _extract_name(self, content: str) -> str:
        """Extract the agent name from the title."""
        match = re.search(r"#\s*Agent_\d+\s*-\s*\"([^\"]+)\"", content)
        if match:
            return match.group(1)
        return "Unknown"

    def load_soul(self, agent_id: str, force_reload: bool = False) -> Optional[AgentSoul]:
        """Load an agent soul from disk."""
        if not force_reload and agent_id in self._cache:
            return self._cache[agent_id]

        soul_path = self.agents_path / agent_id / "soul.md"
        if not soul_path.exists():
            return None

        with open(soul_path, "r") as f:
            content = f.read()

        soul = AgentSoul(
            agent_id=agent_id,
            name=self._extract_name(content),
            personality_summary=self._parse_markdown_text(content, "Core Identity") or
                               self._parse_markdown_text(content, "Personality"),
            strengths=self._parse_markdown_section(content, "Strengths"),
            weaknesses=self._parse_markdown_section(content, "Weaknesses"),
            secret_goal=self._parse_markdown_text(content, "Secret Goal"),
            secret_fear=self._parse_markdown_text(content, "What I Fear") or
                       self._parse_markdown_text(content, "Secret Fear"),
            values=self._parse_markdown_section(content, "What I Value"),
            fears=self._parse_markdown_section(content, "What I Fear"),
            quirks=self._parse_markdown_section(content, "Quirks"),
            communication_style=self._parse_markdown_text(content, "Communication Style"),
            conflict_style=self._parse_markdown_text(content, "Conflict Style"),
            decision_tendencies=self._parse_markdown_section(content, "Decision Tendencies"),
        )

        # Load status if available
        self._load_status(soul)

        self._cache[agent_id] = soul
        return soul

    def _load_status(self, soul: AgentSoul) -> None:
        """Load current status into an existing soul."""
        status_path = self.agents_path / soul.agent_id / "status.md"
        if not status_path.exists():
            return

        with open(status_path, "r") as f:
            content = f.read()

        # Parse current beliefs
        soul.current_beliefs = self._parse_markdown_section(content, "Current Beliefs")

        # Parse emotional state
        match = re.search(r"\*\*Primary\*\*:\s*(\w+)", content)
        if match:
            soul.emotional_state = match.group(1).lower()

        # Parse relationships table
        rel_pattern = r"\|\s*(Agent_\d+)\s*\|\s*(\w+)\s*\((-?\d+)\)"
        for match in re.finditer(rel_pattern, content):
            other_id = match.group(1).lower()
            trust_value = int(match.group(3))
            trust_level = TrustLevel(max(-2, min(2, trust_value)))
            soul.relationships[other_id] = Relationship(
                agent_id=other_id,
                trust_level=trust_level
            )

    def save_status(self, soul: AgentSoul, current_day: int) -> None:
        """Save the current status of an agent to status.md."""
        status_path = self.agents_path / soul.agent_id / "status.md"
        status_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# {soul.agent_id} Status",
            "",
            "## Current State",
            "",
            f"- **Emotional State**: {soul.emotional_state}",
            f"- **Priority Drive**: {soul.drives.get_priority_drive()}",
            "",
            "## Current Beliefs",
            "",
        ]
        for belief in soul.current_beliefs:
            lines.append(f"- {belief}")

        lines.extend([
            "",
            "## Relationships",
            "",
            "| Agent | Trust Level | Last Interaction | Notes |",
            "|-------|-------------|------------------|-------|",
        ])
        for rel in soul.relationships.values():
            trust_name = rel.trust_level.name.replace("_", " ").title()
            last_day = rel.last_interaction_day or "Never"
            notes = "; ".join(rel.notes[-2:]) if rel.notes else ""
            lines.append(f"| {rel.agent_id} | {trust_name} ({rel.trust_level.value}) | {last_day} | {notes} |")

        lines.extend([
            "",
            "---",
            "",
            f"*Last updated: Day {current_day}*",
        ])

        with open(status_path, "w") as f:
            f.write("\n".join(lines))

    def list_agents(self) -> list[str]:
        """List all agent IDs in the world."""
        if not self.agents_path.exists():
            return []

        agents = []
        for path in self.agents_path.iterdir():
            if path.is_dir() and (path / "soul.md").exists():
                agents.append(path.name)
        return sorted(agents)

    def load_all_souls(self) -> dict[str, AgentSoul]:
        """Load all agent souls."""
        souls = {}
        for agent_id in self.list_agents():
            soul = self.load_soul(agent_id)
            if soul:
                souls[agent_id] = soul
        return souls

    def create_agent(self, agent_id: str, name: str,
                    personality: str, secret_goal: str) -> AgentSoul:
        """Create a new agent with minimal configuration."""
        soul = AgentSoul(
            agent_id=agent_id,
            name=name,
            personality_summary=personality,
            secret_goal=secret_goal,
        )

        # Create directory and basic files
        agent_path = self.agents_path / agent_id
        agent_path.mkdir(parents=True, exist_ok=True)

        soul_content = f"""# {agent_id} - "{name}"

## Core Identity

{personality}

## Secret Goal

{secret_goal}

## Personality Traits

### Strengths
*To be discovered through experience*

### Weaknesses
*To be discovered through experience*

## Quirks and Habits

*To be discovered through experience*

## Relationships

### Starting Attitudes
*No prior relationships*

## Communication Style

*Develops through interaction*

## What I Value

*Discovered through choices*

## What I Fear

*Revealed through challenges*

## Conflict Style

*Emerges from necessity*
"""

        with open(agent_path / "soul.md", "w") as f:
            f.write(soul_content)

        self.save_status(soul, current_day=1)
        self._cache[agent_id] = soul

        return soul
