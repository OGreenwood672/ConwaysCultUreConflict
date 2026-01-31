from typing import Optional
from .actions import SimAction, SimActionType


class SimulationInterface:
    """Interface for metamap/game to communicate with AI."""

    def __init__(self):
        self._people_state: dict[int, dict] = {}

    def initialize(self, start_state: list[dict]) -> None:
        """
        Initialize simulation with starting people.

        Args:
            start_state: list of {"id", "culture"} dicts
        """
        self._people_state = {person["id"]: person for person in start_state}

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

    def _llm_decision(self, tick: int, perception: dict) -> SimAction:
        """
        Generate an action using the LLM.

        This is a placeholder for real LLM integration.
        """
        # TODO: Implement real LLM decision making
        action = SimAction(
                    tick=tick,
                    person_id=perception["id"],
                    action_type=SimActionType.IDLE
                )
        return action