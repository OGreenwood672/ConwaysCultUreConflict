"""Daily update engine - end-of-day culture synthesis."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .culture_manager import CultureManager, CultureState
from ..agent.llm_client import LLMClient, ModelTier


@dataclass
class DailyEvent:
    """A significant event from the day."""
    agent_id: str
    action: str
    details: str
    importance: float
    involved_agents: list[str]
    location: Optional[str] = None


class DailyUpdateEngine:
    """
    Synthesizes daily events into culture updates.

    At the end of each game day:
    1. Collects significant events from all agents
    2. Identifies patterns and emergent behaviors
    3. Updates culture.md with new norms, sacred objects, etc.
    4. Records significant events in history.md
    """

    def __init__(self, culture_manager: CultureManager,
                 llm_client: Optional[LLMClient] = None,
                 world_path: str = "world"):
        self.culture_manager = culture_manager
        self.llm_client = llm_client
        self.world_path = Path(world_path)
        self._daily_events: dict[str, list[DailyEvent]] = {}  # culture_id -> events

    def record_event(self, culture_id: str, event: DailyEvent) -> None:
        """Record an event for end-of-day processing."""
        if culture_id not in self._daily_events:
            self._daily_events[culture_id] = []
        self._daily_events[culture_id].append(event)

    def get_daily_events(self, culture_id: str) -> list[DailyEvent]:
        """Get all events recorded for today."""
        return self._daily_events.get(culture_id, [])

    def clear_daily_events(self, culture_id: str) -> None:
        """Clear events after processing."""
        self._daily_events[culture_id] = []

    async def process_day_end(self, culture_id: str, day: int) -> CultureState:
        """
        Process end of day and update culture.

        Returns updated culture state.
        """
        events = self.get_daily_events(culture_id)
        state = self.culture_manager.load_culture(culture_id)

        if not events:
            # No significant events, just advance day
            state.day = day + 1
            self.culture_manager.save_culture(state)
            return state

        # Use LLM to synthesize cultural changes if available
        if self.llm_client:
            updates = await self._llm_synthesize_updates(state, events, day)
        else:
            updates = self._rule_based_updates(state, events, day)

        # Apply updates
        state = self._apply_updates(state, updates, day)

        # Record significant events in history
        self._record_history(culture_id, events, day)

        # Clear processed events
        self.clear_daily_events(culture_id)

        # Save and return
        state.day = day + 1
        self.culture_manager.save_culture(state)

        return state

    async def _llm_synthesize_updates(self, state: CultureState,
                                      events: list[DailyEvent],
                                      day: int) -> dict:
        """Use LLM to synthesize cultural updates from events."""
        events_text = "\n".join(
            f"- {e.agent_id}: {e.action} ({e.details})"
            for e in sorted(events, key=lambda x: -x.importance)[:20]
        )

        norms_text = "\n".join(f"- {n.description}" for n in state.norms) or "None yet"
        sacred_text = "\n".join(f"- {s.name}: {s.significance}" for s in state.sacred_objects) or "None yet"

        prompt = f"""You are analyzing a day's events in a simulated civilization to identify emergent cultural patterns.

Current Day: {day}
Population: {state.population}

Existing Cultural Norms:
{norms_text}

Existing Sacred Objects/Places:
{sacred_text}

Today's Significant Events:
{events_text}

Based on these events, identify any emergent cultural patterns:

1. NEW NORMS: Are any behavioral patterns emerging that could become cultural norms?
   Only suggest norms that are clearly supported by repeated behavior.

2. SACRED OBJECTS: Are any objects or places gaining cultural significance?
   Only suggest if multiple agents show interest or reverence.

3. PRESSURES: What challenges will the culture face tomorrow?

4. SUMMARY: One sentence summary of today's cultural development.

Respond in this exact format:
NEW_NORMS: [list of new norms, or "none"]
SACRED_OBJECTS: [list of object:significance pairs, or "none"]
PRESSURES: [list of pressures]
SUMMARY: [one sentence]

Be conservative - only suggest genuine emergent patterns, not every small event."""

        try:
            response = await self.llm_client.generate(
                prompt,
                tier=ModelTier.BALANCED,
                max_tokens=500,
                temperature=0.5
            )
            return self._parse_llm_response(response)
        except Exception as e:
            print(f"LLM synthesis failed: {e}")
            return self._rule_based_updates(state, events, day)

    def _parse_llm_response(self, response: str) -> dict:
        """Parse LLM response into structured updates."""
        updates = {
            "new_norms": [],
            "sacred_objects": [],
            "pressures": [],
            "summary": ""
        }

        lines = response.strip().split("\n")
        current_key = None

        for line in lines:
            line = line.strip()
            if line.startswith("NEW_NORMS:"):
                current_key = "new_norms"
                content = line[10:].strip()
                if content and content.lower() != "none":
                    updates["new_norms"].extend(self._parse_list(content))
            elif line.startswith("SACRED_OBJECTS:"):
                current_key = "sacred_objects"
                content = line[15:].strip()
                if content and content.lower() != "none":
                    updates["sacred_objects"].extend(self._parse_list(content))
            elif line.startswith("PRESSURES:"):
                current_key = "pressures"
                content = line[10:].strip()
                if content:
                    updates["pressures"].extend(self._parse_list(content))
            elif line.startswith("SUMMARY:"):
                updates["summary"] = line[8:].strip()
            elif current_key and line.startswith("-"):
                item = line[1:].strip()
                if item:
                    updates[current_key].append(item)

        return updates

    def _parse_list(self, content: str) -> list[str]:
        """Parse a comma or semicolon separated list."""
        if content.startswith("[") and content.endswith("]"):
            content = content[1:-1]
        items = []
        for sep in [";", ","]:
            if sep in content:
                items = [i.strip() for i in content.split(sep) if i.strip()]
                break
        if not items and content:
            items = [content]
        return items

    def _rule_based_updates(self, state: CultureState,
                           events: list[DailyEvent], day: int) -> dict:
        """Generate updates using simple rules when LLM unavailable."""
        updates = {
            "new_norms": [],
            "sacred_objects": [],
            "pressures": [],
            "summary": f"Day {day} saw {len(events)} significant events."
        }

        # Count action patterns
        action_counts: dict[str, int] = {}
        agent_interactions: dict[tuple[str, str], int] = {}
        object_mentions: dict[str, int] = {}

        for event in events:
            # Count actions
            action = event.action.lower()
            action_counts[action] = action_counts.get(action, 0) + 1

            # Count interactions
            for other in event.involved_agents:
                pair = tuple(sorted([event.agent_id, other]))
                agent_interactions[pair] = agent_interactions.get(pair, 0) + 1

            # Look for objects in details
            if "orchid" in event.details.lower():
                object_mentions["Blue Orchid"] = object_mentions.get("Blue Orchid", 0) + 1
            if "shrine" in event.details.lower() or "sacred" in event.details.lower():
                object_mentions["shrine"] = object_mentions.get("shrine", 0) + 1

        # Detect emerging norms (actions done 3+ times)
        for action, count in action_counts.items():
            if count >= 3:
                if "trade" in action:
                    updates["new_norms"].append(f"Trading is becoming common practice")
                elif "gather" in action:
                    updates["new_norms"].append(f"Resource gathering is prioritized")

        # Detect sacred objects (mentioned 2+ times)
        for obj, count in object_mentions.items():
            if count >= 2:
                updates["sacred_objects"].append(f"{obj}: Gaining cultural significance")

        # Default pressures based on state
        if state.population > 0:
            updates["pressures"].append("Resource competition may increase")
        if len(state.conflicts) > 0:
            updates["pressures"].append("Ongoing conflicts require resolution")

        return updates

    def _apply_updates(self, state: CultureState, updates: dict,
                      day: int) -> CultureState:
        """Apply parsed updates to culture state."""
        from .culture_manager import CultureNorm, SacredObject

        # Add new norms
        existing_norms = {n.description.lower() for n in state.norms}
        for norm in updates.get("new_norms", []):
            if norm.lower() not in existing_norms:
                state.norms.append(CultureNorm(
                    description=norm,
                    established_day=day,
                    last_reinforced_day=day
                ))

        # Add sacred objects
        existing_sacred = {s.name.lower() for s in state.sacred_objects}
        for item in updates.get("sacred_objects", []):
            if ":" in item:
                name, significance = item.split(":", 1)
            else:
                name = item.split()[0]
                significance = item

            if name.lower() not in existing_sacred:
                state.sacred_objects.append(SacredObject(
                    name=name.strip(),
                    significance=significance.strip(),
                    established_day=day,
                    established_by="community"
                ))

        # Update pressures
        state.current_pressures = updates.get("pressures", [])

        return state

    def _record_history(self, culture_id: str, events: list[DailyEvent],
                       day: int) -> None:
        """Record significant events in history.md."""
        # Sort by importance and take top events
        significant = sorted(events, key=lambda x: -x.importance)[:5]

        history_path = self.culture_manager._get_culture_path(culture_id) / "history.md"

        # Read existing history
        if history_path.exists():
            with open(history_path, "r") as f:
                content = f.read()
        else:
            content = f"# {culture_id.title()} Culture - History Log\n\n"
            content += "A chronological record of significant events.\n\n"

        # Add day section
        content += f"\n---\n\n## Day {day}\n\n"
        for event in significant:
            involved = ", ".join(event.involved_agents) if event.involved_agents else "none"
            content += f"- **{event.agent_id}**: {event.action}\n"
            content += f"  - Details: {event.details}\n"
            if event.involved_agents:
                content += f"  - Involved: {involved}\n"

        with open(history_path, "w") as f:
            f.write(content)

    def get_culture_summary(self, culture_id: str) -> str:
        """Get a brief summary of current culture state."""
        state = self.culture_manager.load_culture(culture_id)

        summary = f"Day {state.day}, Population: {state.population}\n"
        summary += f"Norms: {len(state.norms)}, Sacred Objects: {len(state.sacred_objects)}\n"
        summary += f"Factions: {len(state.factions)}, Active Conflicts: {len([c for c in state.conflicts if not c.resolved])}"

        return summary
