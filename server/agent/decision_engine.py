"""Decision engine - main decision loop for agent behavior."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

from .soul import AgentSoul
from .soul_manager import SoulManager
from .memory import Memory, MemoryType, create_observation
from .memory_store import MemoryStore
from .reflection import ReflectionEngine
from .context_builder import ContextBuilder
from .llm_client import LLMClient, MockLLMClient, ModelTier

from logger import logger


class ActionType(Enum):
    """Types of actions an agent can take."""
    MOVE = "move"
    GATHER = "gather"
    BUILD = "build"
    ATTACK = "attack"
    CHAT = "chat"
    TRADE_OFFER = "trade_offer"
    TRADE_ACCEPT = "trade_accept"
    TRADE_REJECT = "trade_reject"
    WAIT = "wait"
    EXAMINE = "examine"
    CRAFT = "craft"


@dataclass
class Action:
    """Represents an action to be executed."""
    action_type: ActionType
    target: Optional[str] = None
    parameters: dict = field(default_factory=dict)
    reasoning: str = ""
    speech: Optional[str] = None


@dataclass
class DecisionContext:
    """Context for a single decision tick."""
    agent_id: str
    game_day: int
    game_time: str  # dawn, midday, dusk, night
    perception: dict
    available_actions: list[str]


class DecisionEngine:
    """
    Main decision loop for agent behavior.

    Flow per tick:
    1. Load context stack (life -> culture -> soul -> memories)
    2. Receive perception from game adapter
    3. Update drives based on current state
    4. Check if reflection needed -> generate beliefs
    5. LLM outputs action intent
    6. Record decision as memory
    """

    def __init__(self,
                 soul_manager: SoulManager,
                 memory_store: MemoryStore,
                 context_builder: ContextBuilder,
                 llm_client: Optional[LLMClient] = None,
                 use_mock_llm: bool = False):
        self.soul_manager = soul_manager
        self.memory_store = memory_store
        self.context_builder = context_builder
        self.llm_client = llm_client or (MockLLMClient() if use_mock_llm else None)
        self.reflection_engine = ReflectionEngine(memory_store, llm_client)

        # Default actions available
        self.default_actions = [
            "move <direction>",
            "gather <resource>",
            "chat <message>",
            "wait",
            "examine <target>",
        ]

    async def process_tick(self, context: DecisionContext) -> Action:
        """
        Process a single decision tick for an agent.

        Returns the action the agent wants to take.
        """
        # Load soul
        soul = self.soul_manager.load_soul(context.agent_id)
        if not soul:
            return Action(action_type=ActionType.WAIT, reasoning="Soul not found")

        # Update drives based on perception
        self._update_drives(soul, context.perception)

        # Check for reflection trigger
        if self.reflection_engine.should_reflect(context.agent_id):
            await self.reflection_engine.reflect(soul, context.game_day)
            await self.reflection_engine.maybe_form_belief(soul, context.game_day)

        # Retrieve relevant memories
        memories = self.memory_store.retrieve_relevant_memories(
            context.agent_id,
            count=10,
            memory_types=[MemoryType.OBSERVATION, MemoryType.REFLECTION, MemoryType.BELIEF]
        )

        # Build full context
        full_context = self.context_builder.build_full_context(
            soul, memories, context.perception
        )

        # Determine available actions
        available_actions = context.available_actions or self.default_actions

        # Generate decision
        if self.llm_client:
            logger.llm_call(context.agent_id, "decision")
            decision = await self.llm_client.generate_decision(
                full_context,
                self._format_perception(context.perception),
                available_actions
            )
            logger.llm_response(context.agent_id)
        else:
            decision = self._fallback_decision(soul, context)

        # Parse decision into action
        action = self._parse_decision(decision)

        # Log the decision
        logger.decision(context.agent_id, action.action_type.value, action.reasoning)

        # Record decision as memory
        await self._record_decision_memory(
            soul, context, action
        )

        # Save updated soul state
        self.soul_manager.save_status(soul, context.game_day)

        return action

    def _update_drives(self, soul: AgentSoul, perception: dict) -> None:
        """Update agent drives based on current perception."""
        health = perception.get("health", 100)
        hunger = perception.get("hunger", 0)
        has_shelter = perception.get("has_shelter", False)
        relationship_count = len([r for r in soul.relationships.values()
                                 if r.trust_level.value > 0])

        soul.drives.update_from_status(health, hunger, has_shelter, relationship_count)

    def _format_perception(self, perception: dict) -> str:
        """Format perception dict into readable string."""
        lines = []

        if "location" in perception:
            loc = perception["location"]
            lines.append(f"Location: ({loc.get('x', 0)}, {loc.get('y', 0)}, {loc.get('z', 0)})")

        if "nearby_agents" in perception and perception["nearby_agents"]:
            lines.append(f"Nearby agents: {', '.join(perception['nearby_agents'])}")

        if "nearby_entities" in perception and perception["nearby_entities"]:
            lines.append(f"Nearby entities: {', '.join(perception['nearby_entities'][:5])}")

        if "recent_events" in perception and perception["recent_events"]:
            lines.append("Recent events:")
            for event in perception["recent_events"][:3]:
                lines.append(f"  - {event}")

        return "\n".join(lines) if lines else "Nothing notable."

    def _fallback_decision(self, soul: AgentSoul, context: DecisionContext) -> dict:
        """Simple rule-based decision when LLM is unavailable."""
        perception = context.perception

        # Priority 1: Escape danger
        if perception.get("nearby_entities"):
            dangerous = ["zombie", "skeleton", "creeper", "spider"]
            for entity in perception["nearby_entities"]:
                if any(d in entity.lower() for d in dangerous):
                    return {
                        "action": "move",
                        "target": "away from danger",
                        "reasoning": f"Fleeing from {entity}",
                        "speech": None
                    }

        # Priority 2: Address hunger
        if perception.get("hunger", 0) > 60:
            return {
                "action": "gather",
                "target": "food",
                "reasoning": "Getting hungry, need food",
                "speech": None
            }

        # Priority 3: Seek shelter at night
        if context.game_time == "night" and not perception.get("has_shelter"):
            return {
                "action": "build",
                "target": "shelter",
                "reasoning": "Night is dangerous, need shelter",
                "speech": None
            }

        # Priority 4: Social interaction
        if perception.get("nearby_agents"):
            other = perception["nearby_agents"][0]
            return {
                "action": "chat",
                "target": other,
                "reasoning": "Someone nearby, should interact",
                "speech": f"Hello, {other}."
            }

        # Default: Explore based on personality
        priority_drive = soul.drives.get_priority_drive()
        if priority_drive == "cultural":
            return {
                "action": "examine",
                "target": "surroundings",
                "reasoning": "Looking for meaning",
                "speech": None
            }

        return {
            "action": "move",
            "target": "explore",
            "reasoning": "Nothing urgent, exploring",
            "speech": None
        }

    def _parse_decision(self, decision: dict) -> Action:
        """Parse LLM decision dict into Action object."""
        action_str = decision.get("action", "wait").lower()

        # Map action string to ActionType
        action_map = {
            "move": ActionType.MOVE,
            "gather": ActionType.GATHER,
            "build": ActionType.BUILD,
            "attack": ActionType.ATTACK,
            "chat": ActionType.CHAT,
            "trade_offer": ActionType.TRADE_OFFER,
            "trade_accept": ActionType.TRADE_ACCEPT,
            "trade_reject": ActionType.TRADE_REJECT,
            "wait": ActionType.WAIT,
            "examine": ActionType.EXAMINE,
            "craft": ActionType.CRAFT,
        }

        # Handle compound actions like "move north"
        action_type = ActionType.WAIT
        for key, value in action_map.items():
            if action_str.startswith(key):
                action_type = value
                break

        return Action(
            action_type=action_type,
            target=decision.get("target"),
            reasoning=decision.get("reasoning", ""),
            speech=decision.get("speech"),
        )

    async def _record_decision_memory(self, soul: AgentSoul,
                                      context: DecisionContext,
                                      action: Action) -> None:
        """Record the decision as an observation memory."""
        # Determine importance based on action type
        importance_map = {
            ActionType.ATTACK: 8.0,
            ActionType.TRADE_OFFER: 6.0,
            ActionType.TRADE_ACCEPT: 7.0,
            ActionType.CHAT: 4.0,
            ActionType.BUILD: 5.0,
            ActionType.MOVE: 2.0,
            ActionType.WAIT: 1.0,
            ActionType.GATHER: 3.0,
            ActionType.EXAMINE: 3.0,
        }
        importance = importance_map.get(action.action_type, 3.0)

        # Create memory content
        if action.speech:
            content = f"I decided to {action.action_type.value}"
            if action.target:
                content += f" targeting {action.target}"
            content += f" and said: '{action.speech}'"
        else:
            content = f"I decided to {action.action_type.value}"
            if action.target:
                content += f" targeting {action.target}"

        if action.reasoning:
            content += f" because {action.reasoning}"

        memory = create_observation(
            agent_id=context.agent_id,
            content=content,
            importance=importance,
            game_day=context.game_day,
            game_time=context.game_time,
            location=str(context.perception.get("location", "unknown")),
        )

        self.memory_store.add_memory(memory)

    async def process_incoming_chat(self, agent_id: str, sender: str,
                                   message: str, game_day: int,
                                   game_time: str) -> Optional[str]:
        """
        Process an incoming chat message and generate a response.

        Returns the response message or None if no response.
        """
        soul = self.soul_manager.load_soul(agent_id)
        if not soul:
            return None

        # Record incoming message as memory
        memory = create_observation(
            agent_id=agent_id,
            content=f"{sender} said to me: '{message}'",
            importance=5.0,
            game_day=game_day,
            game_time=game_time,
            involved_agents=[sender],
        )
        self.memory_store.add_memory(memory)

        # Update relationship
        soul.record_interaction(sender, game_day)

        # Generate response
        if self.llm_client:
            memories = self.memory_store.retrieve_relevant_memories(agent_id, count=5)
            context = self.context_builder.build_full_context(
                soul, memories, {"nearby_agents": [sender]}
            )
            response = await self.llm_client.generate_chat_response(
                context, message, sender
            )
        else:
            # Fallback response based on personality
            response = self._fallback_chat_response(soul, sender, message)

        # Record outgoing message as memory
        if response:
            response_memory = create_observation(
                agent_id=agent_id,
                content=f"I said to {sender}: '{response}'",
                importance=4.0,
                game_day=game_day,
                game_time=game_time,
                involved_agents=[sender],
            )
            self.memory_store.add_memory(response_memory)

        return response

    def _fallback_chat_response(self, soul: AgentSoul, sender: str,
                                message: str) -> str:
        """Generate a simple response when LLM is unavailable."""
        relationship = soul.get_relationship(sender)

        if relationship.trust_level.value < 0:
            return "I don't have time for this."
        elif relationship.trust_level.value > 0:
            return f"Good to see you, {sender}."
        else:
            return "Hello."

    async def process_event(self, agent_id: str, event_type: str,
                           event_data: dict, game_day: int,
                           game_time: str) -> None:
        """
        Process an external event and record it as a memory.

        Events can be: combat, trade_complete, discovery, etc.
        """
        # Estimate importance
        importance_map = {
            "combat_started": 8.0,
            "combat_won": 7.0,
            "combat_lost": 9.0,
            "trade_complete": 6.0,
            "discovery": 5.0,
            "death_nearby": 8.0,
            "night_started": 4.0,
            "day_started": 3.0,
        }
        importance = importance_map.get(event_type, 5.0)

        # Build event description
        content = event_data.get("description", f"Event: {event_type}")

        memory = create_observation(
            agent_id=agent_id,
            content=content,
            importance=importance,
            game_day=game_day,
            game_time=game_time,
            involved_agents=event_data.get("involved_agents", []),
            related_objects=event_data.get("related_objects", []),
            location=event_data.get("location"),
        )

        self.memory_store.add_memory(memory)
