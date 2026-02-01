"""Dialogue generator - generates pools of conversations between agents."""

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.soul import AgentSoul
from agent.llm_client import LLMClient, MockLLMClient, ModelTier
from culture.culture_manager import CultureState


@dataclass
class DialogueLine:
    """A single line of dialogue."""
    speaker: str  # agent_id
    text: str


@dataclass
class Dialogue:
    """A pre-generated conversation between agents."""
    id: str
    participants: list[str]  # agent_ids
    context: str  # e.g., "greeting_friendly", "trade_negotiation"
    lines: list[DialogueLine]
    used: bool = False


@dataclass
class DialoguePool:
    """Pool of pre-generated dialogues."""
    culture_context: str
    dialogues: list[Dialogue] = field(default_factory=list)

    def get_dialogue(self, participant1: str, participant2: str) -> Optional[Dialogue]:
        """Get an unused dialogue for these participants."""
        for dialogue in self.dialogues:
            if not dialogue.used:
                if (participant1 in dialogue.participants and
                    participant2 in dialogue.participants):
                    return dialogue
        return None

    def mark_used(self, dialogue_id: str) -> None:
        """Mark a dialogue as used."""
        for dialogue in self.dialogues:
            if dialogue.id == dialogue_id:
                dialogue.used = True
                break


class DialogueGenerator:
    """
    Generates pools of conversations between agents.

    Pre-generates dialogue so Mineflayer can pick appropriate
    conversations when agents meet in-game.
    """

    # Context types for dialogue generation
    CONTEXTS = [
        "greeting_friendly",
        "greeting_cautious",
        "trade_negotiation",
        "territorial_tension",
        "alliance_proposal",
        "warning",
        "casual_chat",
        "resource_sharing",
        "conflict_escalation",
        "reconciliation"
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None, use_mock: bool = False):
        if use_mock:
            self.llm_client = MockLLMClient()
        else:
            self.llm_client = llm_client or LLMClient()

    async def generate_pool(
        self,
        agents: dict[str, AgentSoul],
        culture: CultureState,
        dialogues_per_pair: int = 2
    ) -> DialoguePool:
        """
        Generate a pool of dialogues for all agent pairs.

        Args:
            agents: Dict of agent_id -> AgentSoul
            culture: Current cultural state
            dialogues_per_pair: How many dialogues to generate per pair

        Returns:
            DialoguePool with pre-generated conversations
        """
        pool = DialoguePool(
            culture_context=f"Day {culture.day}, {culture.population} agents"
        )

        # Generate dialogues for each pair
        agent_list = list(agents.keys())
        for i, agent1_id in enumerate(agent_list):
            for agent2_id in agent_list[i+1:]:
                soul1 = agents[agent1_id]
                soul2 = agents[agent2_id]

                # Determine appropriate contexts based on relationship
                contexts = self._select_contexts(soul1, soul2)

                for context in contexts[:dialogues_per_pair]:
                    try:
                        dialogue = await self._generate_dialogue(
                            soul1, soul2, context, culture
                        )
                        pool.dialogues.append(dialogue)
                    except Exception:
                        # Skip on error, don't break the whole pool
                        pass

        return pool

    def _select_contexts(self, soul1: AgentSoul, soul2: AgentSoul) -> list[str]:
        """Select appropriate dialogue contexts based on relationship."""
        rel = soul1.relationships.get(soul2.agent_id)

        if rel is None:
            # No relationship yet
            return ["greeting_cautious", "casual_chat"]

        trust = rel.trust_level.value

        if trust >= 1:
            # Friendly
            return ["greeting_friendly", "resource_sharing", "casual_chat", "alliance_proposal"]
        elif trust <= -1:
            # Hostile
            return ["territorial_tension", "warning", "conflict_escalation"]
        else:
            # Neutral
            return ["greeting_cautious", "trade_negotiation", "casual_chat"]

    async def _generate_dialogue(
        self,
        soul1: AgentSoul,
        soul2: AgentSoul,
        context: str,
        culture: CultureState
    ) -> Dialogue:
        """Generate a single dialogue between two agents."""

        prompt = self._build_dialogue_prompt(soul1, soul2, context, culture)

        response = await self.llm_client.generate(
            prompt,
            system_prompt="You are generating Minecraft agent dialogue. Keep it brief and in-character. Respond only with valid JSON.",
            tier=ModelTier.FAST,
            max_tokens=300,
            temperature=0.9
        )

        return self._parse_dialogue_response(soul1.agent_id, soul2.agent_id, context, response)

    def _build_dialogue_prompt(
        self,
        soul1: AgentSoul,
        soul2: AgentSoul,
        context: str,
        culture: CultureState
    ) -> str:
        """Build prompt for dialogue generation."""

        # Get relationship info
        rel1 = soul1.relationships.get(soul2.agent_id)
        rel2 = soul2.relationships.get(soul1.agent_id)

        trust1 = rel1.trust_level.name if rel1 else "NEUTRAL"
        trust2 = rel2.trust_level.name if rel2 else "NEUTRAL"

        # Cultural norms that might affect dialogue
        norm_summary = ""
        if culture.norms:
            norm_summary = "Relevant norms:\n" + "\n".join(
                f"- {n.description}" for n in culture.norms[:3]
            )

        prompt = f"""Generate a short conversation (2-4 lines) between these Minecraft agents:

## Agent 1: {soul1.name} ({soul1.agent_id})
Personality: {soul1.personality_summary[:200]}
Current mood: {soul1.emotional_state}
Communication style: {soul1.communication_style[:100] if soul1.communication_style else "direct"}
How they see {soul2.name}: {trust1}

## Agent 2: {soul2.name} ({soul2.agent_id})
Personality: {soul2.personality_summary[:200]}
Current mood: {soul2.emotional_state}
Communication style: {soul2.communication_style[:100] if soul2.communication_style else "direct"}
How they see {soul1.name}: {trust2}

## Cultural Context
Day {culture.day}
{norm_summary}

## Conversation Context: {context.replace("_", " ")}
(e.g., they just met while exploring, or one approached the other's territory)

Generate realistic dialogue that reflects their personalities and relationship.
Keep it brief - these are in-game chat messages, not essays.

Respond with JSON:
{{
  "context": "<brief situation description>",
  "lines": [
    {{"speaker": "{soul1.agent_id}", "text": "<message>"}},
    {{"speaker": "{soul2.agent_id}", "text": "<message>"}},
    ...
  ]
}}

Response:"""

        return prompt

    def _parse_dialogue_response(
        self,
        agent1_id: str,
        agent2_id: str,
        context: str,
        response: str
    ) -> Dialogue:
        """Parse LLM response into Dialogue object."""
        try:
            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            lines = []
            for line in data.get("lines", []):
                lines.append(DialogueLine(
                    speaker=line["speaker"],
                    text=line["text"]
                ))

            dialogue = Dialogue(
                id=f"d{uuid.uuid4().hex[:6]}",
                participants=[agent1_id, agent2_id],
                context=data.get("context", context),
                lines=lines
            )

            # If lines are empty, use fallback
            if not dialogue.lines:
                return self._fallback_dialogue(agent1_id, agent2_id, context)

            return dialogue
        except (json.JSONDecodeError, KeyError):
            # Fallback to generic dialogue
            return self._fallback_dialogue(agent1_id, agent2_id, context)

    def _fallback_dialogue(self, agent1_id: str, agent2_id: str, context: str) -> Dialogue:
        """Generate a simple fallback dialogue."""
        fallback_lines = {
            "greeting_friendly": [
                DialogueLine(agent1_id, "Good to see you."),
                DialogueLine(agent2_id, "Likewise. How are things?"),
            ],
            "greeting_cautious": [
                DialogueLine(agent1_id, "Hello there."),
                DialogueLine(agent2_id, "...Hi."),
            ],
            "territorial_tension": [
                DialogueLine(agent1_id, "This area is spoken for."),
                DialogueLine(agent2_id, "We'll see about that."),
            ],
            "trade_negotiation": [
                DialogueLine(agent1_id, "Need anything?"),
                DialogueLine(agent2_id, "What do you have?"),
            ],
        }

        lines = fallback_lines.get(context, [
            DialogueLine(agent1_id, "..."),
            DialogueLine(agent2_id, "..."),
        ])

        return Dialogue(
            id=f"d{uuid.uuid4().hex[:6]}",
            participants=[agent1_id, agent2_id],
            context=context,
            lines=lines
        )

    async def generate_single_dialogue(
        self,
        soul1: AgentSoul,
        soul2: AgentSoul,
        context: str,
        culture: CultureState
    ) -> Dialogue:
        """Generate a single dialogue on demand."""
        try:
            return await self._generate_dialogue(soul1, soul2, context, culture)
        except Exception:
            return self._fallback_dialogue(soul1.agent_id, soul2.agent_id, context)
