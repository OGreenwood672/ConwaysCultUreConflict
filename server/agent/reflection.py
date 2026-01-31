"""Reflection engine - LLM-based synthesis of observations into higher-level insights."""

from typing import Optional

from .memory import Memory, MemoryType, create_reflection, create_belief
from .memory_store import MemoryStore
from .soul import AgentSoul


class ReflectionEngine:
    """
    Generates reflections and beliefs from accumulated observations.

    Based on Stanford Generative Agents architecture:
    - Observations accumulate until importance threshold is reached
    - LLM synthesizes observations into reflections
    - Reflections can consolidate into beliefs
    """

    def __init__(self, memory_store: MemoryStore, llm_client: Optional[object] = None):
        self.memory_store = memory_store
        self.llm_client = llm_client
        self.importance_threshold = 3.0  # Trigger reflection when reached

    def should_reflect(self, agent_id: str) -> bool:
        """Check if agent has enough unreflected observations to warrant reflection."""
        unreflected = self.memory_store.get_unreflected_observations(
            agent_id, self.importance_threshold
        )
        return len(unreflected) > 0

    def generate_reflection_prompt(self, soul: AgentSoul,
                                   observations: list[Memory]) -> str:
        """Generate prompt for LLM to create reflections."""
        obs_text = "\n".join(f"- {o.to_context_string()}" for o in observations)

        return f"""You are {soul.name}, reflecting on recent experiences.

Your personality: {soul.personality_summary}
Your values: {', '.join(soul.values[:3]) if soul.values else 'discovering'}

Recent observations:
{obs_text}

Based on these observations, what insights or patterns have you noticed?
Generate 1-3 reflections that synthesize these observations into higher-level understanding.

Format each reflection as a single sentence starting with "I realized..." or "I noticed..." or "It seems that..."

Reflections:"""

    def generate_belief_prompt(self, soul: AgentSoul,
                              reflections: list[Memory]) -> str:
        """Generate prompt for LLM to potentially form beliefs."""
        ref_text = "\n".join(f"- {r.content}" for r in reflections)

        return f"""You are {soul.name}, considering your accumulated insights.

Your personality: {soul.personality_summary}
Your current beliefs: {', '.join(soul.current_beliefs[:3]) if soul.current_beliefs else 'forming'}

Recent reflections:
{ref_text}

Based on these reflections, have you formed any new core beliefs?
A belief is a strong conviction that will guide future decisions.

If a new belief has formed, state it as a single declarative sentence starting with "I believe..."
If no new belief has formed, respond with "No new belief."

Response:"""

    async def reflect(self, soul: AgentSoul, game_day: int) -> list[Memory]:
        """
        Generate reflections from unreflected observations.

        Returns list of new reflection memories.
        """
        if not self.llm_client:
            return self._fallback_reflect(soul, game_day)

        observations = self.memory_store.get_unreflected_observations(
            soul.agent_id, self.importance_threshold
        )

        if not observations:
            return []

        prompt = self.generate_reflection_prompt(soul, observations)

        try:
            response = await self.llm_client.generate(prompt, max_tokens=500)
            reflections = self._parse_reflections(
                soul.agent_id, response, game_day, observations
            )

            # Store reflections
            for reflection in reflections:
                self.memory_store.add_memory(reflection)

            return reflections

        except Exception as e:
            print(f"Reflection generation failed: {e}")
            return self._fallback_reflect(soul, game_day)

    def _fallback_reflect(self, soul: AgentSoul, game_day: int) -> list[Memory]:
        """Simple rule-based reflection when LLM is unavailable."""
        observations = self.memory_store.get_unreflected_observations(
            soul.agent_id, self.importance_threshold
        )

        if not observations:
            return []

        reflections = []

        # Look for patterns
        agents_seen = set()
        locations_visited = set()
        dangers_encountered = False

        for obs in observations:
            agents_seen.update(obs.involved_agents)
            if obs.location:
                locations_visited.add(obs.location)
            if any(word in obs.content.lower() for word in ["zombie", "skeleton", "danger", "attack"]):
                dangers_encountered = True

        # Generate simple reflections
        if len(agents_seen) > 1:
            reflection = create_reflection(
                soul.agent_id,
                f"I've encountered multiple others: {', '.join(agents_seen)}. I should decide who to trust.",
                importance=6.0,
                game_day=game_day,
                source_memories=observations
            )
            reflections.append(reflection)

        if dangers_encountered:
            reflection = create_reflection(
                soul.agent_id,
                "This world has real dangers. I must be more careful.",
                importance=7.0,
                game_day=game_day,
                source_memories=observations
            )
            reflections.append(reflection)

        if len(locations_visited) > 2:
            reflection = create_reflection(
                soul.agent_id,
                f"I've explored several areas. I'm learning the lay of the land.",
                importance=5.0,
                game_day=game_day,
                source_memories=observations
            )
            reflections.append(reflection)

        # Store reflections
        for reflection in reflections:
            self.memory_store.add_memory(reflection)

        return reflections

    def _parse_reflections(self, agent_id: str, llm_response: str,
                          game_day: int, source_observations: list[Memory]) -> list[Memory]:
        """Parse LLM response into reflection memories."""
        reflections = []
        lines = llm_response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove bullet points or numbers
            if line.startswith(("-", "*", "•")):
                line = line[1:].strip()
            elif line[0].isdigit() and line[1:3] in (". ", ") "):
                line = line[3:].strip()

            # Skip if too short or doesn't look like a reflection
            if len(line) < 10:
                continue

            # Estimate importance based on content
            importance = 6.0
            if any(word in line.lower() for word in ["danger", "threat", "enemy", "betrayal"]):
                importance = 8.0
            elif any(word in line.lower() for word in ["trust", "friend", "ally", "safe"]):
                importance = 7.0

            reflection = create_reflection(
                agent_id=agent_id,
                content=line,
                importance=importance,
                game_day=game_day,
                source_memories=source_observations
            )
            reflections.append(reflection)

        return reflections

    async def maybe_form_belief(self, soul: AgentSoul, game_day: int) -> Optional[Memory]:
        """
        Check if recent reflections should consolidate into a belief.

        Returns new belief memory if formed, None otherwise.
        """
        if not self.llm_client:
            return self._fallback_belief(soul, game_day)

        # Get recent reflections
        reflections = self.memory_store.get_recent_memories(
            soul.agent_id, count=5, memory_type=MemoryType.REFLECTION
        )

        if len(reflections) < 3:
            return None

        prompt = self.generate_belief_prompt(soul, reflections)

        try:
            response = await self.llm_client.generate(prompt, max_tokens=100)
            response = response.strip()

            if "no new belief" in response.lower():
                return None

            # Extract belief statement
            if response.lower().startswith("i believe"):
                belief = create_belief(
                    agent_id=soul.agent_id,
                    content=response,
                    game_day=game_day,
                    source_reflections=reflections
                )
                self.memory_store.add_memory(belief)
                soul.add_belief(response)
                return belief

        except Exception as e:
            print(f"Belief formation failed: {e}")

        return None

    def _fallback_belief(self, soul: AgentSoul, game_day: int) -> Optional[Memory]:
        """Simple rule-based belief formation when LLM is unavailable."""
        reflections = self.memory_store.get_recent_memories(
            soul.agent_id, count=10, memory_type=MemoryType.REFLECTION
        )

        if len(reflections) < 3:
            return None

        # Look for repeated themes
        danger_count = sum(1 for r in reflections if "danger" in r.content.lower())
        trust_count = sum(1 for r in reflections if "trust" in r.content.lower())

        belief_content = None

        if danger_count >= 2 and "The world is dangerous" not in soul.current_beliefs:
            belief_content = "I believe the world is dangerous and I must always be prepared."

        elif trust_count >= 2 and "Trust must be earned" not in soul.current_beliefs:
            belief_content = "I believe trust must be earned through actions, not words."

        if belief_content:
            belief = create_belief(
                agent_id=soul.agent_id,
                content=belief_content,
                game_day=game_day,
                source_reflections=reflections
            )
            self.memory_store.add_memory(belief)
            soul.add_belief(belief_content)
            return belief

        return None
