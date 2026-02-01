"""Phase generator - generates high-level behavior phases for each agent."""

import json
import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.soul import AgentSoul
from agent.llm_client import LLMClient, MockLLMClient, ModelTier
from culture.culture_manager import CultureState


class Phase(Enum):
    """High-level behavior modes for agents."""
    BUILD = "BUILD"           # Construction focus
    EXPLORE = "EXPLORE"       # Discovery focus
    AGGRESSIVE = "AGGRESSIVE" # Combat/expansion
    PEACEFUL = "PEACEFUL"     # Social focus
    GATHER = "GATHER"         # Resource collection
    FOLLOW = "FOLLOW"         # Follow specific agent


@dataclass
class AgentPhase:
    """Phase assignment for a single agent."""
    agent_id: str
    phase: Phase
    target: Optional[str]  # Target agent for FOLLOW or AGGRESSIVE
    priority: str  # "high", "medium", "low"
    reasoning: str


class PhaseGenerator:
    """
    Generates high-level behavior phases for each agent.

    Uses LLM to consider personality, culture, and situation when
    deciding what phase each agent should be in.

    Supports staggered processing to avoid blocking all agents.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        use_mock: bool = False,
        batch_size: int = 5,
        llm_ratio: float = 0.3  # What fraction of agents get LLM decisions
    ):
        if use_mock:
            self.llm_client = MockLLMClient()
        else:
            self.llm_client = llm_client or LLMClient()

        self.batch_size = batch_size
        self.llm_ratio = llm_ratio  # 30% LLM, 70% rule-based for speed
        self._llm_queue = []  # Track which agents need LLM next

    async def generate_phases(
        self,
        agents: dict[str, AgentSoul],
        culture: CultureState,
        agent_statuses: Optional[dict[str, dict]] = None
    ) -> dict[str, AgentPhase]:
        """
        Generate phases for all agents using staggered processing.

        - Some agents get LLM-generated phases (rotating selection)
        - Others get fast rule-based phases
        - Batches are processed in parallel

        Args:
            agents: Dict of agent_id -> AgentSoul
            culture: Current cultural state
            agent_statuses: Optional dict of agent_id -> status dict

        Returns:
            Dict of agent_id -> AgentPhase
        """
        phases = {}
        agent_statuses = agent_statuses or {}
        agent_list = list(agents.items())

        # Determine which agents get LLM this round (rotating)
        llm_count = max(1, int(len(agent_list) * self.llm_ratio))
        llm_agents = self._select_llm_agents(agent_list, llm_count)

        # Process in batches
        for i in range(0, len(agent_list), self.batch_size):
            batch = agent_list[i:i + self.batch_size]
            batch_tasks = []

            for agent_id, soul in batch:
                status = agent_statuses.get(agent_id, {})

                if agent_id in llm_agents:
                    # LLM decision (async)
                    task = self._generate_phase_for_agent(soul, culture, status, agents)
                else:
                    # Fast rule-based decision (wrapped as async)
                    task = self._async_fallback(soul, status)

                batch_tasks.append((agent_id, task))

            # Execute batch in parallel
            results = await asyncio.gather(
                *[task for _, task in batch_tasks],
                return_exceptions=True
            )

            # Collect results
            for (agent_id, _), result in zip(batch_tasks, results):
                if isinstance(result, Exception):
                    phases[agent_id] = self._fallback_phase(agents[agent_id], agent_statuses.get(agent_id, {}))
                else:
                    phases[agent_id] = result

        return phases

    def _select_llm_agents(self, agent_list: list, count: int) -> set:
        """
        Select which agents get LLM decisions this round.
        Uses a rotating queue to ensure fairness over time.
        """
        agent_ids = [aid for aid, _ in agent_list]

        # Initialize queue if empty
        if not self._llm_queue or set(self._llm_queue) != set(agent_ids):
            self._llm_queue = agent_ids.copy()
            random.shuffle(self._llm_queue)

        # Pop from front of queue
        selected = set()
        for _ in range(min(count, len(self._llm_queue))):
            if self._llm_queue:
                selected.add(self._llm_queue.pop(0))

        # Refill queue when empty
        if not self._llm_queue:
            self._llm_queue = agent_ids.copy()
            random.shuffle(self._llm_queue)

        return selected

    async def _async_fallback(self, soul: AgentSoul, status: dict) -> AgentPhase:
        """Wrap fallback as async for parallel processing."""
        return self._fallback_phase(soul, status)

    async def _generate_phase_for_agent(
        self,
        soul: AgentSoul,
        culture: CultureState,
        status: dict,
        all_agents: dict[str, AgentSoul]
    ) -> AgentPhase:
        """Generate phase for a single agent using LLM."""

        # Build context
        prompt = self._build_phase_prompt(soul, culture, status, all_agents)

        response = await self.llm_client.generate(
            prompt,
            system_prompt="You are deciding behavior phases for Minecraft agents. Respond only with valid JSON.",
            tier=ModelTier.FAST,
            max_tokens=200,
            temperature=0.7
        )

        # Parse response
        return self._parse_phase_response(soul.agent_id, response)

    def _build_phase_prompt(
        self,
        soul: AgentSoul,
        culture: CultureState,
        status: dict,
        all_agents: dict[str, AgentSoul]
    ) -> str:
        """Build the prompt for phase generation."""

        # Get nearby agents info
        nearby_agents = status.get("nearby_agents", [])
        nearby_info = []
        for agent_id in nearby_agents:
            if agent_id in all_agents:
                other_soul = all_agents[agent_id]
                rel = soul.relationships.get(agent_id)
                trust = rel.trust_level.name if rel else "NEUTRAL"
                nearby_info.append(f"- {other_soul.name} ({agent_id}): {trust}")

        nearby_str = "\n".join(nearby_info) if nearby_info else "None nearby"

        # Culture summary
        culture_summary = self._summarize_culture(culture)

        # Build prompt
        prompt = f"""You are deciding the high-level behavior phase for {soul.name} ({soul.agent_id}).

## Personality
{soul.personality_summary}

Secret goal: {soul.secret_goal}
Secret fear: {soul.secret_fear}
Conflict style: {soul.conflict_style}
Current emotional state: {soul.emotional_state}
Priority drive: {soul.drives.get_priority_drive()}

## Current Culture
{culture_summary}

## Agent Status
- Health: {status.get('health', 20)}/20
- Hunger: {status.get('hunger', 0)}/20
- Has shelter: {status.get('has_shelter', False)}
- Recent events: {status.get('recent_events', 'None')}

## Nearby Agents
{nearby_str}

## Available Phases
- BUILD: Focus on construction (shelter, structures)
- EXPLORE: Discover new areas, find resources
- AGGRESSIVE: Combat, defend territory, confront threats
- PEACEFUL: Social focus, trading, rest, cooperation
- GATHER: Collect resources (mine, chop, harvest)
- FOLLOW: Stay with specific agent (specify target)

What phase should {soul.name} be in? Consider their personality, needs, and situation.

Respond with JSON:
{{
  "phase": "<PHASE_NAME>",
  "target": "<agent_id or null>",
  "priority": "<high|medium|low>",
  "reasoning": "<brief explanation>"
}}

Response:"""

        return prompt

    def _summarize_culture(self, culture: CultureState) -> str:
        """Create a brief summary of culture state."""
        lines = [f"Day {culture.day}, Population: {culture.population}"]

        if culture.factions:
            faction_strs = [f"{f.name} ({len(f.members)} members)" for f in culture.factions]
            lines.append(f"Factions: {', '.join(faction_strs)}")

        if culture.conflicts:
            active = [c for c in culture.conflicts if not c.resolved]
            if active:
                lines.append(f"Active conflicts: {len(active)}")

        if culture.norms:
            lines.append(f"Norms: {len(culture.norms)} established")

        if culture.current_pressures:
            lines.append(f"Pressures: {', '.join(culture.current_pressures[:2])}")

        return "\n".join(lines)

    def _parse_phase_response(self, agent_id: str, response: str) -> AgentPhase:
        """Parse LLM response into AgentPhase."""
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            # Validate phase
            phase_str = data.get("phase", "PEACEFUL").upper()
            try:
                phase = Phase[phase_str]
            except KeyError:
                phase = Phase.PEACEFUL

            return AgentPhase(
                agent_id=agent_id,
                phase=phase,
                target=data.get("target"),
                priority=data.get("priority", "medium"),
                reasoning=data.get("reasoning", "")
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback
            return AgentPhase(
                agent_id=agent_id,
                phase=Phase.PEACEFUL,
                target=None,
                priority="medium",
                reasoning="Failed to parse LLM response"
            )

    def _fallback_phase(self, soul: AgentSoul, status: dict) -> AgentPhase:
        """
        Rule-based fallback with personality-weighted randomness.
        Ensures variety even without LLM.
        """
        priority_drive = soul.drives.get_priority_drive()
        has_shelter = status.get("has_shelter", False)
        health = status.get("health", 20)
        nearby_agents = status.get("nearby_agents", [])

        # Build weighted options based on personality and situation
        weights = {
            Phase.BUILD: 20,
            Phase.EXPLORE: 20,
            Phase.GATHER: 20,
            Phase.PEACEFUL: 20,
            Phase.AGGRESSIVE: 10,
            Phase.FOLLOW: 10,
        }

        # Adjust weights based on drives
        if priority_drive == "survival":
            weights[Phase.GATHER] += 40
            weights[Phase.BUILD] += 20
        elif priority_drive == "safety":
            if not has_shelter:
                weights[Phase.BUILD] += 50
            else:
                weights[Phase.PEACEFUL] += 30
        elif priority_drive == "social":
            weights[Phase.PEACEFUL] += 40
            if nearby_agents:
                weights[Phase.FOLLOW] += 30

        # Adjust for health
        if health < 10:
            weights[Phase.AGGRESSIVE] = 0
            weights[Phase.GATHER] += 30

        # Adjust for nearby threats/allies
        if nearby_agents:
            # Could be allies or threats - add variety
            weights[Phase.AGGRESSIVE] += 15
            weights[Phase.PEACEFUL] += 15

        # Personality-based adjustments using conflict_style
        conflict_style = getattr(soul, 'conflict_style', 'defensive')
        if conflict_style == 'aggressive':
            weights[Phase.AGGRESSIVE] += 25
        elif conflict_style == 'avoidant':
            weights[Phase.EXPLORE] += 25
            weights[Phase.AGGRESSIVE] = 5
        elif conflict_style == 'diplomatic':
            weights[Phase.PEACEFUL] += 25

        # Weighted random selection
        total = sum(weights.values())
        rand = random.random() * total
        cumulative = 0

        selected_phase = Phase.PEACEFUL
        for phase, weight in weights.items():
            cumulative += weight
            if rand <= cumulative:
                selected_phase = phase
                break

        # Generate appropriate reasoning
        reasoning_map = {
            Phase.BUILD: ["Constructing structures", "Building for the future", "Creating shelter"],
            Phase.EXPLORE: ["Seeking new horizons", "Scouting the area", "Discovering resources"],
            Phase.GATHER: ["Collecting resources", "Stockpiling supplies", "Preparing for needs"],
            Phase.PEACEFUL: ["Maintaining harmony", "Resting and socializing", "Building relationships"],
            Phase.AGGRESSIVE: ["Defending territory", "Asserting dominance", "Confronting threats"],
            Phase.FOLLOW: ["Staying with allies", "Supporting the group", "Following leadership"],
        }

        reasoning = random.choice(reasoning_map.get(selected_phase, ["Acting on instinct"]))

        # Determine target for FOLLOW/AGGRESSIVE
        target = None
        if selected_phase == Phase.FOLLOW and nearby_agents:
            target = random.choice(nearby_agents)
        elif selected_phase == Phase.AGGRESSIVE and nearby_agents:
            target = random.choice(nearby_agents)

        return AgentPhase(
            agent_id=soul.agent_id,
            phase=selected_phase,
            target=target,
            priority=random.choice(["high", "medium", "low"]),
            reasoning=reasoning
        )
