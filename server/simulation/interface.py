import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402

import asyncio  # noqa: E402
import re  # noqa: E402
from typing import Optional  # noqa: E402

from actions import SimAction, SimActionType  # noqa: E402
from agent.soul import AgentSoul  # noqa: E402
from agent.soul_manager import SoulManager  # noqa: E402
from agent.llm_client import LLMClient, MockLLMClient, ModelTier  # noqa: E402
from agent.context_builder import ContextBuilder  # noqa: E402

# Mapping from person_id to agent_id
PERSON_TO_AGENT = {
    0: "agent_001",  # The Builder
    1: "agent_002",  # The Seeker
    2: "agent_003",  # The Merchant
}

AVAILABLE_ACTIONS = [
    "move(dx, dy) - Move in a direction. Example: move(1, 0) moves right, move(0, -1) moves up",
    "build(type) - Build at your position. Types: shelter, wall, marker, storage. Example: build(shelter)",
    "communicate(dx, dy) - Talk to someone at that position. Use coordinates from 'Nearby People'. Example: communicate(2, 1)",
]


class SimulationInterface:
    """Interface for metamap/game to communicate with AI."""

    def __init__(self, use_mock_llm: bool = False, world_path: str = "world"):
        self._people_state: dict[int, dict] = {}
        self.use_mock_llm = use_mock_llm
        self.world_path = world_path

        # Initialize components
        self._context_builder = ContextBuilder(world_path)
        self._soul_manager = SoulManager(world_path)
        self._llm_client = MockLLMClient() if use_mock_llm else LLMClient()

        # Cache loaded souls
        self._souls: dict[str, AgentSoul] = {}

        # Store last decisions with full LLM output (for debugging/display)
        self._last_decisions: dict[int, dict] = {}

        # Track daily events for culture updates
        self._daily_events: list[dict] = []
        self._current_day: int = 1

    def initialize(self, start_state: list[dict]) -> None:
        """
        Initialize simulation with starting people.

        Args:
            start_state: list of {"id", "culture"} dicts
        """
        self._people_state = {person["id"]: person for person in start_state}

        # Pre-load souls for all mapped people
        for person_id in self._people_state:
            agent_id = PERSON_TO_AGENT.get(person_id)
            if agent_id:
                soul = self._soul_manager.load_soul(agent_id)
                if soul:
                    self._souls[agent_id] = soul

    def process_tick(self, tick: int, world_state: list[dict]) -> list[dict]:
        """
        Process a tick and return actions for all people.

        Args:
            tick: Current tick number
            world_state: perception for each person

        Returns:
            List of action dicts, one per person
        """
        actions = []

        for person_perception in world_state:
            if self.use_mock_llm:
                action = self._mock_decision(tick, person_perception)
            else:
                action = self._llm_decision(tick, person_perception)

            actions.append(action)

            # Record event for culture tracking
            person_id = person_perception["id"]
            agent_id = PERSON_TO_AGENT.get(person_id, f"person_{person_id}")
            decision = self._last_decisions.get(person_id, {})
            self._daily_events.append(
                {
                    "agent_id": agent_id,
                    "action": action,
                    "reasoning": decision.get("reasoning"),
                    "speech": decision.get("speech"),
                    "tick": tick,
                }
            )

        return actions

    def _get_soul_for_person(self, person_id: int) -> Optional[AgentSoul]:
        """Get the soul for a person, loading if necessary."""
        agent_id = PERSON_TO_AGENT.get(person_id)
        if not agent_id:
            return None

        if agent_id not in self._souls:
            soul = self._soul_manager.load_soul(agent_id)
            if soul:
                self._souls[agent_id] = soul

        return self._souls.get(agent_id)

    def _llm_decision(self, tick: int, perception: dict) -> SimAction:
        """Generate an action using the LLM with full context."""
        person_id = perception["id"]
        soul = self._get_soul_for_person(person_id)

        if not soul:
            # No soul mapping, move randomly
            import random

            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            if dx == 0 and dy == 0:
                dx = 1
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.MOVE,
                x=dx,
                y=dy,
            )

        # Build full context
        context = self._context_builder.build_full_context(
            soul=soul,
            memories=[],  # No memories for now
            perception=perception,
        )

        # Format perception for the prompt
        perception_str = self._format_perception(perception)

        # Call LLM (wrap async in sync)
        decision = asyncio.run(
            self._llm_client.generate_decision(
                context=context,
                perception=perception_str,
                available_actions=AVAILABLE_ACTIONS,
            )
        )

        # Store the full decision for debugging/display
        self._last_decisions[person_id] = decision

        # Parse LLM response into SimAction
        return self._parse_llm_decision(tick, person_id, decision)

    def _mock_decision(self, tick: int, perception: dict) -> SimAction:
        """Generate a mock decision with varied behavior."""
        import random

        person_id = perception["id"]

        # Get nearby people and buildings from perception
        nearby_people = perception.get("relative_people", [])
        nearby_buildings = perception.get("relative_buildings", [])

        # Weight actions based on context
        actions = ["move"] * 5  # Base movement weight
        if nearby_people:
            # More likely to communicate if people nearby
            actions += ["communicate"] * 3
        actions += ["build"] * 2  # Occasional building

        chosen = random.choice(actions)

        if chosen == "communicate" and nearby_people:
            # Communicate with a random nearby person
            target = random.choice(nearby_people)
            dx, dy = target["relative_pos"]
            self._last_decisions[person_id] = {
                "action": f"communicate({dx}, {dy})",
                "reasoning": f"Mock: Communicating with agent {target['id']}",
                "speech": "Hello there!",
            }
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.COMMUNICATE,
                x=dx,
                y=dy,
            )

        elif chosen == "build":
            # Build something
            block_types = ["shelter", "wall", "marker", "storage"]
            block = random.choice(block_types)
            self._last_decisions[person_id] = {
                "action": f"build({block})",
                "reasoning": f"Mock: Building a {block}",
                "speech": None,
            }
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.BUILD,
                target=block,
            )

        else:
            # Move in a random direction
            dx = random.choice([-1, 0, 1])
            dy = random.choice([-1, 0, 1])
            if dx == 0 and dy == 0:
                dx = 1
            self._last_decisions[person_id] = {
                "action": f"move({dx}, {dy})",
                "reasoning": "Mock: Exploring the world",
                "speech": None,
            }
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.MOVE,
                x=dx,
                y=dy,
            )

    def _format_perception(self, perception: dict) -> str:
        """Format perception dict into a readable string."""
        lines = []

        # Basic info
        if "culture" in perception:
            lines.append(f"Your culture: {perception['culture']}")

        # Nearby people (from simulation.py format)
        if "relative_people" in perception and perception["relative_people"]:
            lines.append("\n**Nearby People:**")
            for person in perception["relative_people"]:
                dx, dy = person["relative_pos"]
                same_culture = (
                    "same culture" if person["my_culture"] else "different culture"
                )
                lines.append(f"- Agent {person['id']} at ({dx}, {dy}) - {same_culture}")
                lines.append(f"  To communicate: communicate({dx}, {dy})")

        # Nearby buildings
        if "relative_buildings" in perception and perception["relative_buildings"]:
            lines.append("\n**Nearby Buildings:**")
            for building in perception["relative_buildings"]:
                dx, dy = building["relative_pos"]
                same_culture = "yours" if building["my_culture"] else "other culture"
                lines.append(
                    f"- Building {building['id']} at ({dx}, {dy}) - {same_culture}"
                )

        # Legacy format support
        if "x" in perception and "y" in perception:
            lines.append(f"Position: ({perception['x']}, {perception['y']})")
        if "nearby" in perception:
            lines.append(f"Nearby entities: {perception['nearby']}")
        if "health" in perception:
            lines.append(f"Health: {perception['health']}%")
        if "hunger" in perception:
            lines.append(f"Hunger: {perception['hunger']}%")

        if not lines:
            return "You are alone. Consider building shelter or exploring."

        return "\n".join(lines)

    def get_last_decision(self, person_id: int) -> Optional[dict]:
        """Get the full LLM decision for a person from the last tick."""
        return self._last_decisions.get(person_id)

    def _parse_llm_decision(
        self, tick: int, person_id: int, decision: dict
    ) -> SimAction:
        """Parse LLM decision dict into a SimAction."""
        action_str = decision.get("action", "idle").lower()

        # Parse move(dx, dy)
        move_match = re.match(r"move\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", action_str)
        if move_match:
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.MOVE,
                x=int(move_match.group(1)),
                y=int(move_match.group(2)),
            )

        # Parse communicate(dx, dy)
        comm_match = re.match(
            r"communicate\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", action_str
        )
        if comm_match:
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.COMMUNICATE,
                x=int(comm_match.group(1)),
                y=int(comm_match.group(2)),
            )

        # Parse build(block_type)
        build_match = re.match(r"build\s*\(\s*([^)]+)\s*\)", action_str)
        if build_match:
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.BUILD,
                target=build_match.group(1).strip(),
            )

        # Default to random movement (no idle)
        import random

        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        if dx == 0 and dy == 0:
            dx = 1
        return SimAction(
            tick=tick, person_id=person_id, action_type=SimActionType.MOVE, x=dx, y=dy
        )

    def end_day(self, culture_id: str = "alpha") -> dict:
        """
        End the current day and update culture.md based on agent behavior.

        Args:
            culture_id: The culture to update

        Returns:
            Dict with 'success', 'culture_update', and 'events_processed'
        """
        if not self._daily_events:
            return {
                "success": True,
                "culture_update": None,
                "events_processed": 0,
                "message": "No events to process",
            }

        # Build context for culture update
        context = self._context_builder.build_culture_update_context(
            culture_id=culture_id, daily_events=self._daily_events
        )

        # Generate culture update via LLM
        culture_update = asyncio.run(self._generate_culture_update(context, culture_id))

        # Write updated culture.md
        culture_path = Path(self.world_path) / "cultures" / culture_id / "culture.md"
        culture_path.parent.mkdir(parents=True, exist_ok=True)
        with open(culture_path, "w") as f:
            f.write(culture_update)

        # Invalidate cache so next read gets fresh content
        self._context_builder.invalidate_culture_cache(culture_id)

        # Clear daily events and increment day
        events_count = len(self._daily_events)
        self._daily_events = []
        self._current_day += 1

        return {
            "success": True,
            "culture_update": culture_update,
            "events_processed": events_count,
            "day": self._current_day,
        }

    async def _generate_culture_update(self, context: str, culture_id: str) -> str:
        """Generate updated culture.md content via LLM."""
        prompt = f"""{context}

---

Based on today's events, write an updated culture.md file for Day {self._current_day + 1}.

Update the following sections based on what happened:
- Current State (day number, any new factions, conflicts)
- Established Norms (patterns of behavior that repeated)
- Economic Patterns (any trading, resource sharing)
- Social Structure (leadership emerging, alliances, rivalries)
- Recent Events (summary of today's significant events)
- Cultural Memory (any events significant enough to remember)

Keep sections that haven't changed. Only add to Cultural Memory for truly significant events.

Write the complete updated culture.md file:"""

        if self.use_mock_llm:
            # Mock response for testing
            return f"""# {culture_id.title()} Culture - Day {self._current_day + 1}

## Current State

- **Day**: {self._current_day + 1}
- **Population**: 3 agents
- **Events Today**: {len(self._daily_events)} actions recorded

## Recent Events

*Day {self._current_day}*
{chr(10).join(f"- {e['agent_id']}: {e['action']}" for e in self._daily_events[:5])}

---

*Mock culture update - use real LLM for meaningful updates.*
"""

        response = await self._llm_client.generate(
            prompt=prompt,
            system_prompt="You are a cultural historian documenting the evolution of a society. Write in markdown format.",
            tier=ModelTier.BALANCED,
            max_tokens=2000,
            temperature=0.7,
        )

        return response.strip()
