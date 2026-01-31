import asyncio
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from .actions import SimAction, SimActionType
from agent.context_builder import ContextBuilder
from agent.llm_client import LLMClient, MockLLMClient
from agent.soul_manager import SoulManager
from agent.soul import AgentSoul


# Mapping from person_id to agent_id
PERSON_TO_AGENT = {
    0: "agent_001",  # The Builder
    1: "agent_002",  # The Seeker
    2: "agent_003",  # The Merchant
}

AVAILABLE_ACTIONS = [
    "move(dx, dy) - Move relative to current position",
    "build(block_type) - Build a structure",
    "communicate(dx, dy) - Communicate with someone at relative position",
    "idle - Do nothing and observe",
]


class SimulationInterface:
    """Interface for metamap/game to communicate with AI."""

    def __init__(self, use_mock_llm: bool = True, world_path: str = "world"):
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

            actions.append(action.to_dict())

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
            # No soul mapping, return idle
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.IDLE
            )

        # Build full context
        context = self._context_builder.build_full_context(
            soul=soul,
            memories=[],  # No memories for now
            perception=perception
        )

        # Format perception for the prompt
        perception_str = self._format_perception(perception)

        # Call LLM (wrap async in sync)
        decision = asyncio.run(
            self._llm_client.generate_decision(
                context=context,
                perception=perception_str,
                available_actions=AVAILABLE_ACTIONS
            )
        )

        # Store the full decision for debugging/display
        self._last_decisions[person_id] = decision

        # Parse LLM response into SimAction
        return self._parse_llm_decision(tick, person_id, decision)

    def _mock_decision(self, tick: int, perception: dict) -> SimAction:
        """Generate a mock decision for testing."""
        person_id = perception["id"]
        # Simple pattern: alternate between move and idle
        if tick % 2 == 0:
            self._last_decisions[person_id] = {
                "action": "move(1, 0)",
                "reasoning": "Mock: Moving to explore",
                "speech": None
            }
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.MOVE,
                x=1,
                y=0
            )
        self._last_decisions[person_id] = {
            "action": "idle",
            "reasoning": "Mock: Observing surroundings",
            "speech": None
        }
        return SimAction(
            tick=tick,
            person_id=person_id,
            action_type=SimActionType.IDLE
        )

    def _format_perception(self, perception: dict) -> str:
        """Format perception dict into a readable string."""
        lines = []
        if "x" in perception and "y" in perception:
            lines.append(f"Position: ({perception['x']}, {perception['y']})")
        if "culture" in perception:
            lines.append(f"Culture: {perception['culture']}")
        if "nearby" in perception:
            lines.append(f"Nearby entities: {perception['nearby']}")
        if "health" in perception:
            lines.append(f"Health: {perception['health']}%")
        if "hunger" in perception:
            lines.append(f"Hunger: {perception['hunger']}%")
        return "\n".join(lines) if lines else "No additional perception data."

    def get_last_decision(self, person_id: int) -> Optional[dict]:
        """Get the full LLM decision for a person from the last tick."""
        return self._last_decisions.get(person_id)

    def _parse_llm_decision(self, tick: int, person_id: int, decision: dict) -> SimAction:
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
                y=int(move_match.group(2))
            )

        # Parse communicate(dx, dy)
        comm_match = re.match(r"communicate\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", action_str)
        if comm_match:
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.COMMUNICATE,
                x=int(comm_match.group(1)),
                y=int(comm_match.group(2))
            )

        # Parse build(block_type)
        build_match = re.match(r"build\s*\(\s*([^)]+)\s*\)", action_str)
        if build_match:
            return SimAction(
                tick=tick,
                person_id=person_id,
                action_type=SimActionType.BUILD,
                target=build_match.group(1).strip()
            )

        # Default to idle
        return SimAction(
            tick=tick,
            person_id=person_id,
            action_type=SimActionType.IDLE
        )