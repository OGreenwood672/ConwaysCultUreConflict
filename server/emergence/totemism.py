"""Totemism system - seeds arbitrary value to create economics and religion."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import random


class TotemType(Enum):
    """Types of totems/sacred objects."""
    NATURAL = "natural"        # Flowers, trees, stones
    CRAFTED = "crafted"       # Built shrines, artifacts
    LOCATION = "location"     # Sacred places
    CREATURE = "creature"     # Sacred animals
    CONCEPT = "concept"       # Abstract beliefs


@dataclass
class Totem:
    """A totem - an object or concept with cultural significance."""
    id: str
    name: str
    totem_type: TotemType
    description: str

    # Value and significance
    base_value: float = 1.0  # Economic value multiplier
    cultural_significance: float = 0.0  # 0-10, grows with worship/attention
    mystery_level: float = 5.0  # How unexplained its significance is

    # Origin
    discovered_by: str = ""
    discovered_day: int = 1
    origin_story: str = ""

    # Believers
    believers: set[str] = field(default_factory=set)
    skeptics: set[str] = field(default_factory=set)

    # Physical properties
    location: Optional[str] = None
    is_portable: bool = True
    quantity_known: int = 0  # How many exist (0 = unknown)

    # Rituals
    associated_rituals: list[str] = field(default_factory=list)


@dataclass
class Ritual:
    """A ritual associated with a totem or belief."""
    id: str
    name: str
    description: str
    totem_id: Optional[str] = None

    # Requirements
    required_participants: int = 1
    required_items: list[str] = field(default_factory=list)
    required_location: Optional[str] = None
    required_time: Optional[str] = None  # dawn, dusk, night, etc.

    # Effects
    effect_description: str = ""
    participants_affected: list[str] = field(default_factory=list)

    # History
    times_performed: int = 0
    last_performed_day: Optional[int] = None
    created_by: str = ""
    created_day: int = 1


@dataclass
class Belief:
    """A belief held by agents."""
    id: str
    content: str
    related_totem_id: Optional[str] = None

    # Adherents
    believers: set[str] = field(default_factory=set)
    strength: float = 0.5  # 0-1, how strongly held

    # Origin
    originated_from: str = ""  # agent or event
    created_day: int = 1


class TotemismSystem:
    """
    Seeds arbitrary value into objects to create emergent economics and religion.

    Key mechanisms:
    - Certain objects are marked as potentially significant
    - Agent attention/collection increases significance
    - Significance creates economic value
    - Shared belief creates religious structures
    - Rituals reinforce and spread beliefs
    """

    def __init__(self):
        self.totems: dict[str, Totem] = {}
        self.rituals: dict[str, Ritual] = {}
        self.beliefs: dict[str, Belief] = {}
        self._totem_counter = 0
        self._ritual_counter = 0
        self._belief_counter = 0

        # Seed some potentially significant items
        self._seed_potential_totems()

    def _seed_potential_totems(self) -> None:
        """Seed initial potential totems that agents might discover."""
        seeds = [
            ("Blue Orchid", TotemType.NATURAL, "A rare flower with an ethereal blue color", True),
            ("First Stone", TotemType.NATURAL, "The first stone placed in any structure", False),
            ("Sunrise Point", TotemType.LOCATION, "The highest point where sunrise is first visible", False),
            ("Ancient Oak", TotemType.NATURAL, "An unusually large and old tree", False),
            ("Cave Crystal", TotemType.NATURAL, "Crystals found deep in caves", True),
            ("Wolf", TotemType.CREATURE, "The wolf - hunter and pack animal", False),
        ]

        for name, ttype, desc, portable in seeds:
            self._totem_counter += 1
            totem = Totem(
                id=f"totem_{self._totem_counter}",
                name=name,
                totem_type=ttype,
                description=desc,
                is_portable=portable,
                base_value=1.0 + random.random(),
                mystery_level=random.uniform(3, 8),
            )
            self.totems[totem.id] = totem

    def discover_totem(self, totem_name: str, agent_id: str,
                      day: int, location: Optional[str] = None) -> Optional[Totem]:
        """Record an agent discovering/noticing a potential totem."""
        # Find matching totem
        totem = None
        for t in self.totems.values():
            if t.name.lower() == totem_name.lower():
                totem = t
                break

        if not totem:
            # Create new totem
            self._totem_counter += 1
            totem = Totem(
                id=f"totem_{self._totem_counter}",
                name=totem_name,
                totem_type=TotemType.NATURAL,
                description=f"A {totem_name} that caught someone's attention",
                discovered_by=agent_id,
                discovered_day=day,
                location=location,
            )
            self.totems[totem.id] = totem

        if not totem.discovered_by:
            totem.discovered_by = agent_id
            totem.discovered_day = day

        if location and not totem.location:
            totem.location = location

        # Increase significance through discovery
        totem.cultural_significance = min(10, totem.cultural_significance + 0.5)
        totem.believers.add(agent_id)

        return totem

    def show_interest(self, totem_id: str, agent_id: str) -> bool:
        """Record an agent showing interest in a totem."""
        if totem_id not in self.totems:
            return False

        totem = self.totems[totem_id]
        totem.believers.add(agent_id)
        totem.cultural_significance = min(10, totem.cultural_significance + 0.3)
        totem.base_value = min(10, totem.base_value * 1.1)

        return True

    def express_skepticism(self, totem_id: str, agent_id: str) -> bool:
        """Record an agent expressing skepticism about a totem."""
        if totem_id not in self.totems:
            return False

        totem = self.totems[totem_id]
        totem.skeptics.add(agent_id)
        totem.believers.discard(agent_id)

        # Skepticism reduces significance slightly
        if len(totem.skeptics) > len(totem.believers):
            totem.cultural_significance = max(0, totem.cultural_significance - 0.2)

        return True

    def create_ritual(self, name: str, description: str,
                     creator: str, day: int,
                     totem_id: Optional[str] = None,
                     required_items: Optional[list[str]] = None,
                     required_time: Optional[str] = None) -> Ritual:
        """Create a new ritual."""
        self._ritual_counter += 1
        ritual_id = f"ritual_{self._ritual_counter}"

        ritual = Ritual(
            id=ritual_id,
            name=name,
            description=description,
            totem_id=totem_id,
            required_items=required_items or [],
            required_time=required_time,
            created_by=creator,
            created_day=day,
        )

        self.rituals[ritual_id] = ritual

        # Link to totem if specified
        if totem_id and totem_id in self.totems:
            self.totems[totem_id].associated_rituals.append(ritual_id)

        return ritual

    def perform_ritual(self, ritual_id: str, participants: list[str],
                      day: int, location: Optional[str] = None) -> dict:
        """Perform a ritual."""
        if ritual_id not in self.rituals:
            return {"success": False, "reason": "Ritual not found"}

        ritual = self.rituals[ritual_id]

        # Check requirements
        if len(participants) < ritual.required_participants:
            return {"success": False, "reason": "Not enough participants"}

        # Record performance
        ritual.times_performed += 1
        ritual.last_performed_day = day
        ritual.participants_affected.extend(participants)

        # Increase totem significance if linked
        if ritual.totem_id and ritual.totem_id in self.totems:
            totem = self.totems[ritual.totem_id]
            totem.cultural_significance = min(10, totem.cultural_significance + 0.5)
            for p in participants:
                totem.believers.add(p)

        return {
            "success": True,
            "ritual_name": ritual.name,
            "participants": participants,
            "times_performed": ritual.times_performed,
        }

    def create_belief(self, content: str, originator: str, day: int,
                     totem_id: Optional[str] = None) -> Belief:
        """Create a new belief."""
        self._belief_counter += 1
        belief_id = f"belief_{self._belief_counter}"

        belief = Belief(
            id=belief_id,
            content=content,
            related_totem_id=totem_id,
            believers={originator},
            originated_from=originator,
            created_day=day,
        )

        self.beliefs[belief_id] = belief
        return belief

    def adopt_belief(self, belief_id: str, agent_id: str) -> bool:
        """Have an agent adopt a belief."""
        if belief_id not in self.beliefs:
            return False

        belief = self.beliefs[belief_id]
        belief.believers.add(agent_id)
        belief.strength = min(1.0, belief.strength + 0.1)

        return True

    def reject_belief(self, belief_id: str, agent_id: str) -> bool:
        """Have an agent reject a belief."""
        if belief_id not in self.beliefs:
            return False

        belief = self.beliefs[belief_id]
        belief.believers.discard(agent_id)

        if len(belief.believers) == 0:
            belief.strength = max(0.1, belief.strength - 0.2)

        return True

    def get_economic_value(self, item_name: str) -> float:
        """Get the economic value of an item based on totemism."""
        base_value = 1.0

        for totem in self.totems.values():
            if totem.name.lower() == item_name.lower():
                # Value based on cultural significance and believer count
                significance_multiplier = 1 + (totem.cultural_significance / 5)
                believer_multiplier = 1 + (len(totem.believers) * 0.2)
                scarcity_multiplier = 1 / max(1, totem.quantity_known / 10)

                return totem.base_value * significance_multiplier * believer_multiplier * scarcity_multiplier

        return base_value

    def get_shared_beliefs(self, agents: list[str]) -> list[Belief]:
        """Get beliefs shared by all specified agents."""
        if not agents:
            return []

        shared = []
        for belief in self.beliefs.values():
            if all(a in belief.believers for a in agents):
                shared.append(belief)

        return shared

    def get_agent_totems(self, agent_id: str) -> list[Totem]:
        """Get totems an agent believes in."""
        return [t for t in self.totems.values() if agent_id in t.believers]

    def process_day(self, current_day: int) -> dict:
        """Process daily updates for totemism."""
        results = {
            "significance_changes": [],
            "value_changes": [],
        }

        for totem in self.totems.values():
            # Natural decay of significance without reinforcement
            if totem.cultural_significance > 1:
                old_sig = totem.cultural_significance
                totem.cultural_significance = max(1, totem.cultural_significance - 0.1)
                if abs(old_sig - totem.cultural_significance) > 0.05:
                    results["significance_changes"].append({
                        "totem": totem.name,
                        "old": old_sig,
                        "new": totem.cultural_significance,
                    })

        return results

    def get_cultural_report(self) -> dict:
        """Get a report of current cultural/religious state."""
        # Sort totems by significance
        sorted_totems = sorted(
            self.totems.values(),
            key=lambda t: t.cultural_significance,
            reverse=True
        )

        active_beliefs = [b for b in self.beliefs.values() if len(b.believers) > 0]
        active_rituals = [r for r in self.rituals.values() if r.times_performed > 0]

        return {
            "most_significant_totems": [
                {"name": t.name, "significance": t.cultural_significance, "believers": len(t.believers)}
                for t in sorted_totems[:5]
            ],
            "active_beliefs": len(active_beliefs),
            "active_rituals": len(active_rituals),
            "total_ritual_performances": sum(r.times_performed for r in self.rituals.values()),
        }

    def get_totem_by_name(self, name: str) -> Optional[Totem]:
        """Find a totem by name."""
        for totem in self.totems.values():
            if totem.name.lower() == name.lower():
                return totem
        return None
