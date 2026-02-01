"""Culture updater - tracks emergent economics, religion, ethics at population level."""

import json
from dataclasses import dataclass
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.soul import AgentSoul
from agent.llm_client import LLMClient, MockLLMClient, ModelTier
from culture.culture_manager import CultureManager, CultureState, CultureNorm, SacredObject, Faction


@dataclass
class CultureEvent:
    """An event that might affect culture."""
    description: str
    agent_id: str
    involved_agents: list[str]
    event_type: str  # "trade", "conflict", "discovery", "ritual", etc.
    importance: int = 5  # 1-10


class CultureUpdater:
    """
    Updates culture.md based on agent behavior and events.

    Tracks emergent:
    - Economics (trade values, resource scarcity)
    - Religion (sacred objects, rituals, beliefs)
    - Ethics (norms, taboos, expectations)
    - Social structure (factions, alliances, conflicts)
    """

    def __init__(
        self,
        culture_manager: Optional[CultureManager] = None,
        llm_client: Optional[LLMClient] = None,
        use_mock: bool = False
    ):
        self.culture_manager = culture_manager or CultureManager()
        if use_mock:
            self.llm_client = MockLLMClient()
        else:
            self.llm_client = llm_client or LLMClient()

        # Buffer of events since last update
        self._event_buffer: list[CultureEvent] = []

    def record_event(self, event: CultureEvent) -> None:
        """Record an event for later processing."""
        self._event_buffer.append(event)

    def get_pending_events(self) -> list[CultureEvent]:
        """Get events pending processing."""
        return self._event_buffer.copy()

    def clear_events(self) -> None:
        """Clear the event buffer."""
        self._event_buffer.clear()

    async def update(
        self,
        agents: dict[str, AgentSoul],
        culture_id: str = "alpha",
        events: Optional[list[CultureEvent]] = None
    ) -> CultureState:
        """
        Update culture based on agent states and recent events.

        Args:
            agents: Dict of agent_id -> AgentSoul
            culture_id: Which culture to update
            events: Optional list of events (uses buffer if not provided)

        Returns:
            Updated CultureState
        """
        # Get current state
        culture = self.culture_manager.load_culture(culture_id, force_reload=True)

        # Use provided events or buffer
        events_to_process = events or self._event_buffer

        if not events_to_process:
            # No events, just update population
            culture.population = len(agents)
            self.culture_manager.save_culture(culture)
            return culture

        # Generate culture updates using LLM
        try:
            updates = await self._analyze_events(culture, agents, events_to_process)
            culture = self._apply_updates(culture, updates)
        except Exception:
            # Fallback to rule-based updates
            culture = self._rule_based_update(culture, agents, events_to_process)

        # Update population
        culture.population = len(agents)

        # Save
        self.culture_manager.save_culture(culture)

        # Clear buffer if we used it
        if events is None:
            self.clear_events()

        return culture

    async def _analyze_events(
        self,
        culture: CultureState,
        agents: dict[str, AgentSoul],
        events: list[CultureEvent]
    ) -> dict:
        """Use LLM to analyze events and suggest culture updates."""

        prompt = self._build_analysis_prompt(culture, agents, events)

        response = await self.llm_client.generate(
            prompt,
            system_prompt="You are analyzing emergent culture in a Minecraft simulation. Respond only with valid JSON.",
            tier=ModelTier.BALANCED,  # Use better model for culture analysis
            max_tokens=500,
            temperature=0.7
        )

        return self._parse_analysis_response(response)

    def _build_analysis_prompt(
        self,
        culture: CultureState,
        agents: dict[str, AgentSoul],
        events: list[CultureEvent]
    ) -> str:
        """Build prompt for culture analysis."""

        # Current state summary
        current_norms = "\n".join(f"- {n.description}" for n in culture.norms[:5]) or "None yet"
        current_sacred = "\n".join(f"- {s.name}: {s.significance}" for s in culture.sacred_objects[:3]) or "None yet"

        # Agent summary
        agent_summary = []
        for aid, soul in agents.items():
            agent_summary.append(f"- {soul.name}: {soul.personality_summary[:80]}...")
        agent_str = "\n".join(agent_summary[:6])

        # Events
        event_strs = []
        for e in events[-20:]:  # Last 20 events
            event_strs.append(f"- [{e.event_type}] {e.description} (by {e.agent_id})")
        events_str = "\n".join(event_strs) or "No recent events"

        prompt = f"""Analyze recent events and suggest culture updates for a Minecraft civilization.

## Current Culture State (Day {culture.day})
Population: {culture.population} agents

### Current Norms
{current_norms}

### Sacred Objects/Places
{current_sacred}

### Current Factions
{len(culture.factions)} factions formed

## Agents
{agent_str}

## Recent Events
{events_str}

Based on these events, identify:
1. New norms that might be forming (repeated behaviors becoming expectations)
2. Objects/places gaining sacred significance
3. Emerging economic patterns (trade values, scarcity)
4. Faction dynamics (alliances, tensions)
5. Tomorrow's likely pressures

Respond with JSON:
{{
  "new_norms": [
    {{"description": "<norm description>", "strength": <1-10>}}
  ],
  "new_sacred_objects": [
    {{"name": "<name>", "significance": "<why it matters>"}}
  ],
  "trade_updates": {{
    "<resource>": <relative_value>
  }},
  "new_pressures": ["<pressure1>", "<pressure2>"],
  "faction_updates": [
    {{"action": "create|merge|dissolve", "name": "<name>", "members": ["<agent_ids>"]}}
  ],
  "day_summary": "<one sentence summary of cultural shift>"
}}

Response:"""

        return prompt

    def _parse_analysis_response(self, response: str) -> dict:
        """Parse LLM analysis response."""
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    def _apply_updates(self, culture: CultureState, updates: dict) -> CultureState:
        """Apply LLM-suggested updates to culture."""

        # Add new norms
        for norm_data in updates.get("new_norms", []):
            # Check if similar norm already exists
            exists = any(
                norm_data["description"].lower() in n.description.lower()
                for n in culture.norms
            )
            if not exists:
                culture.norms.append(CultureNorm(
                    description=norm_data["description"],
                    established_day=culture.day,
                    strength=norm_data.get("strength", 1.0)
                ))

        # Add sacred objects
        for obj_data in updates.get("new_sacred_objects", []):
            exists = any(
                obj_data["name"].lower() == s.name.lower()
                for s in culture.sacred_objects
            )
            if not exists:
                culture.sacred_objects.append(SacredObject(
                    name=obj_data["name"],
                    significance=obj_data["significance"],
                    established_day=culture.day,
                    established_by="collective"
                ))

        # Update trade values
        for resource, value in updates.get("trade_updates", {}).items():
            culture.trade_values[resource] = float(value)

        # Update pressures
        culture.current_pressures = updates.get("new_pressures", culture.current_pressures)

        # Handle faction updates
        for faction_update in updates.get("faction_updates", []):
            action = faction_update.get("action")
            if action == "create":
                culture.factions.append(Faction(
                    name=faction_update["name"],
                    members=faction_update.get("members", []),
                    formed_day=culture.day
                ))
            elif action == "dissolve":
                culture.factions = [
                    f for f in culture.factions
                    if f.name != faction_update["name"]
                ]

        # Log summary to history
        summary = updates.get("day_summary", "Culture continues to evolve.")
        self.culture_manager.append_to_history(culture.culture_id, summary, culture.day)

        return culture

    def _rule_based_update(
        self,
        culture: CultureState,
        agents: dict[str, AgentSoul],
        events: list[CultureEvent]
    ) -> CultureState:
        """Fallback rule-based culture update."""

        # Count event types
        event_counts = {}
        for e in events:
            event_counts[e.event_type] = event_counts.get(e.event_type, 0) + 1

        # If lots of trades, add trade norm
        if event_counts.get("trade", 0) >= 3:
            exists = any("trade" in n.description.lower() for n in culture.norms)
            if not exists:
                culture.norms.append(CultureNorm(
                    description="Trade is encouraged among community members",
                    established_day=culture.day
                ))

        # If lots of conflicts, add pressure
        if event_counts.get("conflict", 0) >= 2:
            if "internal tensions" not in culture.current_pressures:
                culture.current_pressures.append("internal tensions")

        # Track agent groupings as potential factions
        # (Simple heuristic based on trust levels)
        high_trust_pairs = []
        for aid, soul in agents.items():
            for other_id, rel in soul.relationships.items():
                if rel.trust_level.value >= 1 and other_id in agents:
                    high_trust_pairs.append((aid, other_id))

        # If enough trust pairs, might form faction
        if len(high_trust_pairs) >= 3 and len(culture.factions) == 0:
            # Find connected agents
            connected = set()
            for a, b in high_trust_pairs:
                connected.add(a)
                connected.add(b)

            if len(connected) >= 2:
                culture.factions.append(Faction(
                    name="Alliance",
                    members=list(connected),
                    formed_day=culture.day
                ))

        return culture

    async def advance_day(self, culture_id: str = "alpha") -> CultureState:
        """Advance culture to next day and process pending events."""
        culture = await self.update({}, culture_id)
        culture.day += 1
        self.culture_manager.save_culture(culture)
        return culture
