"""Runtime - ties all agent components together."""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path

from .soul import AgentSoul
from .soul_manager import SoulManager
from .memory_store import MemoryStore
from .reflection import ReflectionEngine
from .context_builder import ContextBuilder
from .decision_engine import DecisionEngine, DecisionContext, Action
from .llm_client import LLMClient, LLMConfig, MockLLMClient


@dataclass
class GameTime:
    """Represents current game time."""
    day: int = 1
    period: str = "dawn"  # dawn, midday, dusk, night
    tick: int = 0

    def advance_tick(self) -> None:
        """Advance time by one tick."""
        self.tick += 1
        # Assume 100 ticks per period
        if self.tick >= 100:
            self.tick = 0
            periods = ["dawn", "midday", "dusk", "night"]
            current_idx = periods.index(self.period)
            self.period = periods[(current_idx + 1) % len(periods)]
            if self.period == "dawn":
                self.day += 1

    def is_night(self) -> bool:
        return self.period == "night"

    def is_day_end(self) -> bool:
        return self.period == "night" and self.tick == 99


@dataclass
class AgentRuntime:
    """
    Runtime manager for a single agent.

    Handles the main loop, perception processing, and action execution.
    """
    agent_id: str
    soul: AgentSoul
    decision_engine: DecisionEngine
    memory_store: MemoryStore

    # Callbacks
    on_action: Optional[Callable[[str, Action], Any]] = None
    on_chat: Optional[Callable[[str, str, str], Any]] = None  # agent_id, target, message

    # State
    current_perception: dict = field(default_factory=dict)
    pending_actions: list[Action] = field(default_factory=list)
    is_running: bool = False

    async def update_perception(self, perception: dict) -> None:
        """Update agent's current perception of the world."""
        self.current_perception = perception

    async def tick(self, game_time: GameTime) -> Optional[Action]:
        """Process a single tick of the simulation."""
        if not self.is_running:
            return None

        context = DecisionContext(
            agent_id=self.agent_id,
            game_day=game_time.day,
            game_time=game_time.period,
            perception=self.current_perception,
            available_actions=self._get_available_actions()
        )

        action = await self.decision_engine.process_tick(context)

        if self.on_action:
            await self._call_callback(self.on_action, self.agent_id, action)

        if action.speech and self.on_chat:
            target = action.target or "everyone"
            await self._call_callback(self.on_chat, self.agent_id, target, action.speech)

        return action

    async def _call_callback(self, callback: Callable, *args) -> Any:
        """Call a callback, handling both sync and async."""
        result = callback(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    def _get_available_actions(self) -> list[str]:
        """Determine available actions based on current state."""
        actions = ["wait", "examine surroundings"]

        # Movement always available
        actions.extend(["move north", "move south", "move east", "move west"])

        # Check inventory for tools
        inventory = self.current_perception.get("inventory", [])
        has_tool = any("pickaxe" in str(i).lower() or "axe" in str(i).lower()
                       for i in inventory)

        # Gathering based on nearby resources
        nearby_blocks = self.current_perception.get("nearby_blocks", [])
        if nearby_blocks:
            for block in nearby_blocks[:3]:
                block_type = block.get("type", "resource")
                actions.append(f"gather {block_type}")

        # Combat if enemies nearby
        nearby_entities = self.current_perception.get("nearby_entities", [])
        dangerous = ["zombie", "skeleton", "creeper", "spider"]
        for entity in nearby_entities[:3]:
            if any(d in entity.lower() for d in dangerous):
                actions.append(f"attack {entity}")
                actions.append(f"flee from {entity}")

        # Social if agents nearby
        nearby_agents = self.current_perception.get("nearby_agents", [])
        for agent in nearby_agents[:3]:
            actions.append(f"chat with {agent}")
            actions.append(f"trade with {agent}")

        # Building if has materials
        if has_tool or any("wood" in str(i).lower() or "stone" in str(i).lower()
                          for i in inventory):
            actions.append("build shelter")
            actions.append("build wall")

        return actions

    async def handle_incoming_chat(self, sender: str, message: str,
                                   game_time: GameTime) -> Optional[str]:
        """Handle an incoming chat message."""
        return await self.decision_engine.process_incoming_chat(
            self.agent_id, sender, message, game_time.day, game_time.period
        )

    async def handle_event(self, event_type: str, event_data: dict,
                          game_time: GameTime) -> None:
        """Handle an external event."""
        await self.decision_engine.process_event(
            self.agent_id, event_type, event_data,
            game_time.day, game_time.period
        )

    def start(self) -> None:
        """Start the agent runtime."""
        self.is_running = True

    def stop(self) -> None:
        """Stop the agent runtime."""
        self.is_running = False


class SimulationRuntime:
    """
    Main simulation runtime that manages all agents.

    Coordinates the simulation loop, handles inter-agent communication,
    and manages game time.
    """

    def __init__(self, world_path: str = "world",
                 use_mock_llm: bool = False,
                 llm_config: Optional[LLMConfig] = None):
        self.world_path = Path(world_path)

        # Initialize core components
        self.soul_manager = SoulManager(str(world_path))
        self.memory_store = MemoryStore(str(world_path))
        self.context_builder = ContextBuilder(str(world_path))

        # Initialize LLM
        if use_mock_llm:
            self.llm_client = MockLLMClient()
        elif llm_config:
            self.llm_client = LLMClient(llm_config)
        else:
            self.llm_client = None

        # Initialize decision engine
        self.decision_engine = DecisionEngine(
            soul_manager=self.soul_manager,
            memory_store=self.memory_store,
            context_builder=self.context_builder,
            llm_client=self.llm_client
        )

        # Agent runtimes
        self.agents: dict[str, AgentRuntime] = {}
        self.game_time = GameTime()

        # Callbacks
        self.on_action: Optional[Callable] = None
        self.on_chat: Optional[Callable] = None
        self.on_day_end: Optional[Callable] = None

        # State
        self.is_running = False

    def load_agents(self) -> None:
        """Load all agents from the world directory."""
        for agent_id in self.soul_manager.list_agents():
            self.add_agent(agent_id)

    def add_agent(self, agent_id: str) -> Optional[AgentRuntime]:
        """Add an agent to the simulation."""
        soul = self.soul_manager.load_soul(agent_id)
        if not soul:
            return None

        runtime = AgentRuntime(
            agent_id=agent_id,
            soul=soul,
            decision_engine=self.decision_engine,
            memory_store=self.memory_store,
            on_action=self._handle_agent_action,
            on_chat=self._handle_agent_chat,
        )

        self.agents[agent_id] = runtime
        return runtime

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the simulation."""
        if agent_id in self.agents:
            self.agents[agent_id].stop()
            del self.agents[agent_id]

    async def _handle_agent_action(self, agent_id: str, action: Action) -> None:
        """Handle an action from an agent."""
        if self.on_action:
            result = self.on_action(agent_id, action)
            if asyncio.iscoroutine(result):
                await result

    async def _handle_agent_chat(self, agent_id: str, target: str,
                                message: str) -> None:
        """Handle chat from one agent, potentially routing to others."""
        if self.on_chat:
            result = self.on_chat(agent_id, target, message)
            if asyncio.iscoroutine(result):
                await result

        # Route to target agent if it exists
        if target in self.agents:
            response = await self.agents[target].handle_incoming_chat(
                agent_id, message, self.game_time
            )
            if response and self.on_chat:
                result = self.on_chat(target, agent_id, response)
                if asyncio.iscoroutine(result):
                    await result

    async def tick(self) -> dict[str, Optional[Action]]:
        """Process a single simulation tick for all agents."""
        actions = {}

        for agent_id, runtime in self.agents.items():
            action = await runtime.tick(self.game_time)
            actions[agent_id] = action

        # Advance time
        was_day_end = self.game_time.is_day_end()
        self.game_time.advance_tick()

        # Trigger day end callback
        if was_day_end and self.on_day_end:
            result = self.on_day_end(self.game_time.day - 1)
            if asyncio.iscoroutine(result):
                await result

        return actions

    async def run(self, tick_interval: float = 0.5,
                 max_ticks: Optional[int] = None) -> None:
        """Run the main simulation loop."""
        self.is_running = True

        for runtime in self.agents.values():
            runtime.start()

        tick_count = 0
        while self.is_running:
            if max_ticks and tick_count >= max_ticks:
                break

            await self.tick()
            tick_count += 1

            await asyncio.sleep(tick_interval)

        for runtime in self.agents.values():
            runtime.stop()

    def stop(self) -> None:
        """Stop the simulation."""
        self.is_running = False

    def update_agent_perception(self, agent_id: str, perception: dict) -> None:
        """Update perception for a specific agent."""
        if agent_id in self.agents:
            asyncio.create_task(self.agents[agent_id].update_perception(perception))

    def broadcast_event(self, event_type: str, event_data: dict,
                       exclude_agents: Optional[list[str]] = None) -> None:
        """Broadcast an event to all agents."""
        exclude = exclude_agents or []
        for agent_id, runtime in self.agents.items():
            if agent_id not in exclude:
                asyncio.create_task(
                    runtime.handle_event(event_type, event_data, self.game_time)
                )

    def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """Get the current status of an agent."""
        if agent_id not in self.agents:
            return None

        runtime = self.agents[agent_id]
        soul = runtime.soul

        return {
            "agent_id": agent_id,
            "name": soul.name,
            "is_running": runtime.is_running,
            "emotional_state": soul.emotional_state,
            "priority_drive": soul.drives.get_priority_drive(),
            "belief_count": len(soul.current_beliefs),
            "relationship_count": len(soul.relationships),
        }

    def get_simulation_status(self) -> dict:
        """Get overall simulation status."""
        return {
            "is_running": self.is_running,
            "game_day": self.game_time.day,
            "game_period": self.game_time.period,
            "tick": self.game_time.tick,
            "agent_count": len(self.agents),
            "agents": [self.get_agent_status(aid) for aid in self.agents],
        }
