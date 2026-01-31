"""Information system - manages information asymmetry and rumors."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import random


@dataclass
class Information:
    """A piece of information that can spread between agents."""
    id: str
    content: str
    source_agent: str
    created_day: int

    # Truth and accuracy
    is_true: bool = True
    accuracy: float = 1.0  # 0-1, degrades as info spreads
    original_content: str = ""  # The original true content

    # Spread tracking
    known_by: set[str] = field(default_factory=set)
    spread_count: int = 0

    # Metadata
    category: str = "general"  # resource, danger, agent, location, event
    importance: float = 5.0  # 1-10
    location: Optional[str] = None
    related_agents: list[str] = field(default_factory=list)
    expires_day: Optional[int] = None  # Day when info becomes outdated


@dataclass
class Rumor:
    """A rumor - potentially distorted information."""
    id: str
    content: str
    original_info_id: Optional[str] = None
    source_agent: str = ""
    created_day: int = 1

    # Credibility
    credibility: float = 0.5  # 0-1
    times_heard: int = 1  # More = more credible (social proof)
    contradicted_by: list[str] = field(default_factory=list)  # Info IDs that contradict

    # Spread
    known_by: set[str] = field(default_factory=set)


class InformationSystem:
    """
    Manages information asymmetry to encourage social behavior and tribalism.

    Key mechanisms:
    - Agents have imperfect perception (can't see everything)
    - Information degrades as it spreads (telephone game)
    - Rumors can form from partial information
    - Reputation information spreads through gossip
    - Groups form around shared (true or false) beliefs
    """

    def __init__(self):
        self.information: dict[str, Information] = {}
        self.rumors: dict[str, Rumor] = {}
        self.agent_knowledge: dict[str, set[str]] = {}  # agent -> info IDs they know
        self._info_counter = 0
        self._rumor_counter = 0

    def create_information(self, content: str, source_agent: str,
                          day: int, category: str = "general",
                          importance: float = 5.0,
                          location: Optional[str] = None,
                          related_agents: Optional[list[str]] = None,
                          expires_day: Optional[int] = None) -> Information:
        """Create a new piece of true information."""
        self._info_counter += 1
        info_id = f"info_{self._info_counter}"

        info = Information(
            id=info_id,
            content=content,
            source_agent=source_agent,
            created_day=day,
            is_true=True,
            accuracy=1.0,
            original_content=content,
            known_by={source_agent},
            category=category,
            importance=importance,
            location=location,
            related_agents=related_agents or [],
            expires_day=expires_day,
        )

        self.information[info_id] = info
        self._add_to_agent_knowledge(source_agent, info_id)

        return info

    def share_information(self, info_id: str, from_agent: str,
                         to_agent: str, day: int) -> Optional[Information]:
        """
        Share information from one agent to another.

        Information may degrade in accuracy during transmission.
        """
        if info_id not in self.information:
            return None

        info = self.information[info_id]

        if from_agent not in info.known_by:
            return None  # Can't share what you don't know

        if to_agent in info.known_by:
            return info  # Already knows

        # Calculate degradation
        degradation = random.uniform(0.85, 0.98)
        new_accuracy = info.accuracy * degradation

        # Potentially mutate the content slightly
        if random.random() > new_accuracy:
            info.content = self._mutate_content(info.content)
            if info.content != info.original_content:
                info.is_true = False

        info.accuracy = new_accuracy
        info.known_by.add(to_agent)
        info.spread_count += 1

        self._add_to_agent_knowledge(to_agent, info_id)

        return info

    def _mutate_content(self, content: str) -> str:
        """Slightly alter content to simulate telephone game effect."""
        mutations = [
            lambda s: s.replace("some", "many"),
            lambda s: s.replace("many", "some"),
            lambda s: s.replace("might", "will"),
            lambda s: s.replace("will", "might"),
            lambda s: s.replace("dangerous", "very dangerous"),
            lambda s: s.replace("safe", "relatively safe"),
            lambda s: s + " (I think)",
        ]

        if random.random() < 0.3:  # 30% chance of mutation
            mutation = random.choice(mutations)
            return mutation(content)
        return content

    def create_rumor(self, content: str, source_agent: str, day: int,
                    original_info_id: Optional[str] = None) -> Rumor:
        """Create a new rumor (unverified information)."""
        self._rumor_counter += 1
        rumor_id = f"rumor_{self._rumor_counter}"

        rumor = Rumor(
            id=rumor_id,
            content=content,
            original_info_id=original_info_id,
            source_agent=source_agent,
            created_day=day,
            credibility=0.3,  # Rumors start with low credibility
            known_by={source_agent},
        )

        self.rumors[rumor_id] = rumor
        return rumor

    def spread_rumor(self, rumor_id: str, from_agent: str,
                    to_agent: str) -> Optional[Rumor]:
        """Spread a rumor to another agent."""
        if rumor_id not in self.rumors:
            return None

        rumor = self.rumors[rumor_id]

        if from_agent not in rumor.known_by:
            return None

        if to_agent in rumor.known_by:
            # Already heard - increases credibility
            rumor.times_heard += 1
            rumor.credibility = min(0.9, rumor.credibility + 0.1)
        else:
            rumor.known_by.add(to_agent)
            rumor.times_heard += 1

        return rumor

    def verify_rumor(self, rumor_id: str, is_true: bool,
                    verifying_info_id: Optional[str] = None) -> None:
        """Mark a rumor as verified or debunked."""
        if rumor_id not in self.rumors:
            return

        rumor = self.rumors[rumor_id]

        if is_true:
            rumor.credibility = 1.0
            # Convert to information
            self._info_counter += 1
            info = Information(
                id=f"info_{self._info_counter}",
                content=rumor.content,
                source_agent=rumor.source_agent,
                created_day=rumor.created_day,
                is_true=True,
                accuracy=1.0,
                original_content=rumor.content,
                known_by=rumor.known_by.copy(),
            )
            self.information[info.id] = info
        else:
            rumor.credibility = 0.0
            if verifying_info_id:
                rumor.contradicted_by.append(verifying_info_id)

    def _add_to_agent_knowledge(self, agent_id: str, info_id: str) -> None:
        """Add information to an agent's knowledge base."""
        if agent_id not in self.agent_knowledge:
            self.agent_knowledge[agent_id] = set()
        self.agent_knowledge[agent_id].add(info_id)

    def get_agent_knowledge(self, agent_id: str,
                           category: Optional[str] = None) -> list[Information]:
        """Get all information known by an agent."""
        if agent_id not in self.agent_knowledge:
            return []

        info_ids = self.agent_knowledge[agent_id]
        infos = [self.information[i] for i in info_ids if i in self.information]

        if category:
            infos = [i for i in infos if i.category == category]

        return sorted(infos, key=lambda x: x.importance, reverse=True)

    def get_agent_rumors(self, agent_id: str) -> list[Rumor]:
        """Get all rumors known by an agent."""
        return [r for r in self.rumors.values() if agent_id in r.known_by]

    def get_reputation_info(self, about_agent: str,
                           asking_agent: str) -> list[Information]:
        """Get information about an agent's reputation."""
        if asking_agent not in self.agent_knowledge:
            return []

        reputation_info = []
        for info_id in self.agent_knowledge[asking_agent]:
            if info_id in self.information:
                info = self.information[info_id]
                if about_agent in info.related_agents or about_agent in info.content:
                    reputation_info.append(info)

        return reputation_info

    def create_false_information(self, content: str, source_agent: str,
                                day: int, target_agent: Optional[str] = None) -> Information:
        """Create intentionally false information (lie)."""
        self._info_counter += 1
        info_id = f"info_{self._info_counter}"

        info = Information(
            id=info_id,
            content=content,
            source_agent=source_agent,
            created_day=day,
            is_true=False,
            accuracy=0.0,
            original_content="[FABRICATED]",
            known_by={source_agent},
            category="deception",
            related_agents=[target_agent] if target_agent else [],
        )

        self.information[info_id] = info
        return info

    def process_day(self, current_day: int) -> None:
        """Process daily information updates."""
        # Expire old information
        expired_ids = []
        for info_id, info in self.information.items():
            if info.expires_day and current_day > info.expires_day:
                expired_ids.append(info_id)

        for info_id in expired_ids:
            del self.information[info_id]
            # Remove from agent knowledge
            for agent_id in self.agent_knowledge:
                self.agent_knowledge[agent_id].discard(info_id)

        # Decay rumor credibility over time
        for rumor in self.rumors.values():
            age = current_day - rumor.created_day
            if age > 5:  # Old rumors lose credibility
                rumor.credibility = max(0.1, rumor.credibility - 0.05)

    def get_information_asymmetry(self, agent1: str, agent2: str) -> dict:
        """Calculate information asymmetry between two agents."""
        knowledge1 = self.agent_knowledge.get(agent1, set())
        knowledge2 = self.agent_knowledge.get(agent2, set())

        shared = knowledge1 & knowledge2
        only_agent1 = knowledge1 - knowledge2
        only_agent2 = knowledge2 - knowledge1

        return {
            "shared": len(shared),
            "only_agent1": len(only_agent1),
            "only_agent2": len(only_agent2),
            "asymmetry_score": abs(len(only_agent1) - len(only_agent2)) /
                              max(1, len(knowledge1 | knowledge2)),
        }

    def get_common_beliefs(self, agents: list[str]) -> list[Information]:
        """Get information shared by all specified agents."""
        if not agents:
            return []

        common_ids = None
        for agent_id in agents:
            agent_knowledge = self.agent_knowledge.get(agent_id, set())
            if common_ids is None:
                common_ids = agent_knowledge.copy()
            else:
                common_ids &= agent_knowledge

        if not common_ids:
            return []

        return [self.information[i] for i in common_ids if i in self.information]
