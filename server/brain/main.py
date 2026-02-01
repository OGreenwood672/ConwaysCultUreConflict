"""Main brain service - continuous loop that generates phases and dialogue."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.soul_manager import SoulManager
from agent.llm_client import LLMClient, MockLLMClient
from culture.culture_manager import CultureManager

from .phase_generator import PhaseGenerator
from .dialogue_generator import DialogueGenerator
from .culture_updater import CultureUpdater, CultureEvent
from .output_writer import OutputWriter


class BrainService:
    """
    Main AI Brain Service that runs continuously.

    Generates:
    1. Phases for each agent (what high-level behavior they should do)
    2. Dialogue pools (pre-generated conversations)
    3. Culture updates (emergent economics, religion, ethics)
    """

    def __init__(
        self,
        world_path: str = "world",
        output_dir: str = "output",
        use_mock_llm: bool = False,
        culture_id: str = "alpha"
    ):
        # Core managers
        self.soul_manager = SoulManager(world_path)
        self.culture_manager = CultureManager(world_path)

        # LLM client (shared across generators)
        if use_mock_llm:
            self.llm_client = MockLLMClient()
        else:
            self.llm_client = LLMClient()

        # Generators
        self.phase_generator = PhaseGenerator(self.llm_client, use_mock=use_mock_llm)
        self.dialogue_generator = DialogueGenerator(self.llm_client, use_mock=use_mock_llm)
        self.culture_updater = CultureUpdater(
            self.culture_manager,
            self.llm_client,
            use_mock=use_mock_llm
        )

        # Output writer
        self.output_writer = OutputWriter(output_dir)

        # Configuration
        self.default_culture_id = culture_id  # Fallback culture
        self.use_mock_llm = use_mock_llm

        # Cache for loaded cultures
        self._cultures: dict[str, any] = {}

        # State tracking
        self._running = False
        self._last_phase_update = None
        self._last_dialogue_refresh = None
        self._last_culture_update = None
        self._last_game_state_time = None
        self._agent_statuses: dict[str, dict] = {}

        # Game state file (written by Mineflayer bots)
        self.game_state_file = Path(output_dir) / "game_state.json"

        # Timing configuration (in seconds)
        self.phase_interval = 2.0       # How often to update phases
        self.dialogue_threshold = 5     # Refresh dialogues when below this count
        self.culture_interval = 60.0    # How often to update culture

    async def run(self, max_iterations: Optional[int] = None) -> None:
        """
        Run the brain service loop.

        Args:
            max_iterations: Optional limit on iterations (for testing)
        """
        self._running = True
        iteration = 0

        print(f"[Brain] Starting AI Brain Service (mock={self.use_mock_llm})")
        print(f"[Brain] Output dir: {self.output_writer.output_dir}")

        while self._running:
            try:
                await self._brain_tick()

                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    break

                # Brief pause between iterations
                await asyncio.sleep(self.phase_interval)

            except KeyboardInterrupt:
                print("[Brain] Shutting down...")
                break
            except Exception as e:
                print(f"[Brain] Error in brain loop: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retry

        self._running = False
        print("[Brain] Brain service stopped")

    async def _generate_phases_multi_culture(self, agents: dict) -> dict:
        """Generate phases for agents, each with their own culture context."""
        from .phase_generator import AgentPhase

        all_phases = {}

        # Group agents by culture for efficiency
        agents_by_culture: dict[str, dict] = {}
        for agent_id, soul in agents.items():
            culture_id = soul.culture_id
            if culture_id not in agents_by_culture:
                agents_by_culture[culture_id] = {}
            agents_by_culture[culture_id][agent_id] = soul

        # Generate phases per culture group
        for culture_id, culture_agents in agents_by_culture.items():
            culture = self._cultures.get(culture_id)
            if not culture:
                # Fallback to default culture
                culture = self._cultures.get(self.default_culture_id)
                if not culture:
                    culture = self.culture_manager.load_culture(self.default_culture_id)
                    self._cultures[self.default_culture_id] = culture

            # Generate phases for this culture's agents
            phases = await self.phase_generator.generate_phases(
                culture_agents, culture, self._agent_statuses
            )
            all_phases.update(phases)

        return all_phases

    def _read_game_state(self) -> Optional[dict]:
        """Read game state from Mineflayer bots."""
        try:
            if not self.game_state_file.exists():
                return None

            with open(self.game_state_file, "r") as f:
                state = json.load(f)

            # Check if state is fresh (within last 5 seconds)
            timestamp = state.get("timestamp")
            if timestamp == self._last_game_state_time:
                return None  # No new data

            self._last_game_state_time = timestamp

            # Convert game state to agent statuses format
            for agent_id, agent_data in state.get("agents", {}).items():
                self._agent_statuses[agent_id] = {
                    "health": agent_data.get("health", 20),
                    "hunger": 20 - agent_data.get("food", 20),  # Convert food to hunger
                    "has_shelter": agent_data.get("structuresBuilt", 0) > 0,
                    "nearby_agents": [n["id"] for n in agent_data.get("nearbyAgents", [])],
                    "position": agent_data.get("position"),
                    "current_phase": agent_data.get("currentPhase"),
                    "is_building": agent_data.get("isBuilding", False)
                }

            return state
        except Exception as e:
            print(f"[Brain] Error reading game state: {e}")
            return None

    async def _brain_tick(self) -> None:
        """Single tick of the brain service."""

        # 1. Read game state from Mineflayer
        game_state = self._read_game_state()

        # 2. Load agent souls
        agents = self.soul_manager.load_all_souls()

        if not agents:
            # No agents defined in soul files, nothing to do
            return

        # 3. Load cultures for each agent
        cultures_needed = set(soul.culture_id for soul in agents.values())
        for culture_id in cultures_needed:
            if culture_id not in self._cultures:
                self._cultures[culture_id] = self.culture_manager.load_culture(culture_id)

        # 4. Generate phases (per-agent with their culture)
        phases = await self._generate_phases_multi_culture(agents)
        self.output_writer.write_phases(phases)
        self._last_phase_update = datetime.utcnow()

        if game_state:
            print(f"[Brain] Generated phases for {len(phases)} agents across {len(cultures_needed)} cultures")

        # 5. Check if dialogue pool needs refresh
        if self._dialogue_pool_needs_refresh():
            print("[Brain] Refreshing dialogue pool...")
            # Use default culture for cross-culture dialogue context
            default_culture = self._cultures.get(self.default_culture_id) or \
                              self.culture_manager.load_culture(self.default_culture_id)
            pool = await self.dialogue_generator.generate_pool(agents, default_culture)
            self.output_writer.write_dialogues(pool)
            self._last_dialogue_refresh = datetime.utcnow()
            print(f"[Brain] Generated {len(pool.dialogues)} dialogues")

        # 6. Update all active cultures
        if self._should_update_culture():
            print("[Brain] Updating cultures...")
            for culture_id in self._cultures.keys():
                culture_agents = {aid: soul for aid, soul in agents.items()
                                  if soul.culture_id == culture_id}
                if culture_agents:
                    await self.culture_updater.update(culture_agents, culture_id)
            self._last_culture_update = datetime.utcnow()

    def _dialogue_pool_needs_refresh(self) -> bool:
        """Check if dialogue pool needs refreshing."""
        # No pool exists yet
        if self._last_dialogue_refresh is None:
            return True

        # Pool is running low on unused dialogues
        unused = self.output_writer.get_unused_dialogue_count()
        if unused < self.dialogue_threshold:
            return True

        return False

    def _should_update_culture(self) -> bool:
        """Check if culture should be updated."""
        # Never updated
        if self._last_culture_update is None:
            return True

        # Check interval
        elapsed = (datetime.utcnow() - self._last_culture_update).total_seconds()
        if elapsed >= self.culture_interval:
            return True

        # Check if pending events
        if len(self.culture_updater.get_pending_events()) >= 10:
            return True

        return False

    def update_agent_status(self, agent_id: str, status: dict) -> None:
        """
        Update an agent's status (called by external game bridge).

        Args:
            agent_id: The agent's ID
            status: Dict with health, hunger, has_shelter, nearby_agents, etc.
        """
        self._agent_statuses[agent_id] = status

    def record_event(self, event: CultureEvent) -> None:
        """Record an event for culture processing."""
        self.culture_updater.record_event(event)

    def stop(self) -> None:
        """Stop the brain service."""
        self._running = False

    def get_status(self) -> dict:
        """Get current brain service status."""
        return {
            "running": self._running,
            "use_mock_llm": self.use_mock_llm,
            "default_culture_id": self.default_culture_id,
            "active_cultures": list(self._cultures.keys()),
            "last_phase_update": self._last_phase_update.isoformat() if self._last_phase_update else None,
            "last_dialogue_refresh": self._last_dialogue_refresh.isoformat() if self._last_dialogue_refresh else None,
            "last_culture_update": self._last_culture_update.isoformat() if self._last_culture_update else None,
            "tracked_agents": len(self._agent_statuses),
            "pending_culture_events": len(self.culture_updater.get_pending_events()),
            "output_status": self.output_writer.get_output_status()
        }


async def main():
    """Entry point for running the brain service."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Brain Service")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM client")
    parser.add_argument("--world", default="world", help="Path to world directory")
    parser.add_argument("--output", default="output", help="Path to output directory")
    parser.add_argument("--culture", default="alpha", help="Culture ID to use")
    args = parser.parse_args()

    brain = BrainService(
        world_path=args.world,
        output_dir=args.output,
        use_mock_llm=args.mock,
        culture_id=args.culture
    )

    await brain.run()


if __name__ == "__main__":
    asyncio.run(main())
