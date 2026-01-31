"""Scarcity system - manages resource availability to force trade/conflict."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import random


class ResourceCategory(Enum):
    """Categories of resources."""
    FOOD = "food"
    BUILDING = "building"
    TOOL = "tool"
    RARE = "rare"
    LUXURY = "luxury"


@dataclass
class Resource:
    """Represents a type of resource in the world."""
    name: str
    category: ResourceCategory
    base_abundance: float = 1.0  # 0-1 scale, 1 = common
    current_abundance: float = 1.0
    regeneration_rate: float = 0.1  # Per day
    max_abundance: float = 1.0
    min_abundance: float = 0.1

    # Location constraints
    biome_preferences: list[str] = field(default_factory=list)  # Biomes where more common
    seasonal_modifier: dict[str, float] = field(default_factory=dict)  # season -> multiplier


@dataclass
class ScarcityEvent:
    """An event that affects resource scarcity."""
    event_type: str  # drought, abundance, discovery, depletion
    affected_resources: list[str]
    modifier: float  # Multiplier to apply
    duration_days: int
    days_remaining: int
    description: str


class ScarcitySystem:
    """
    Manages resource scarcity to encourage emergent economic behavior.

    Key mechanisms:
    - Resource abundance varies by location and time
    - Consumption depletes local resources
    - Events can cause shortages or windfalls
    - Trade becomes necessary when local resources are scarce
    """

    def __init__(self):
        self.resources: dict[str, Resource] = {}
        self.regional_abundance: dict[str, dict[str, float]] = {}  # region -> resource -> abundance
        self.active_events: list[ScarcityEvent] = []
        self.consumption_history: dict[str, float] = {}  # resource -> total consumed

        self._initialize_resources()

    def _initialize_resources(self) -> None:
        """Initialize default resource types."""
        # Food resources
        self.resources["wheat"] = Resource(
            name="wheat",
            category=ResourceCategory.FOOD,
            base_abundance=0.7,
            biome_preferences=["plains", "forest"],
            seasonal_modifier={"spring": 0.5, "summer": 1.2, "fall": 1.0, "winter": 0.3}
        )
        self.resources["meat"] = Resource(
            name="meat",
            category=ResourceCategory.FOOD,
            base_abundance=0.5,
            biome_preferences=["plains", "forest", "taiga"],
        )
        self.resources["fish"] = Resource(
            name="fish",
            category=ResourceCategory.FOOD,
            base_abundance=0.6,
            biome_preferences=["ocean", "river"],
        )

        # Building resources
        self.resources["wood"] = Resource(
            name="wood",
            category=ResourceCategory.BUILDING,
            base_abundance=0.8,
            biome_preferences=["forest", "taiga"],
            regeneration_rate=0.05,
        )
        self.resources["stone"] = Resource(
            name="stone",
            category=ResourceCategory.BUILDING,
            base_abundance=0.9,
            biome_preferences=["mountains", "hills"],
            regeneration_rate=0.0,  # Doesn't regenerate
        )
        self.resources["clay"] = Resource(
            name="clay",
            category=ResourceCategory.BUILDING,
            base_abundance=0.4,
            biome_preferences=["river", "swamp"],
        )

        # Tool resources
        self.resources["iron"] = Resource(
            name="iron",
            category=ResourceCategory.TOOL,
            base_abundance=0.3,
            biome_preferences=["mountains", "caves"],
            regeneration_rate=0.0,
        )
        self.resources["coal"] = Resource(
            name="coal",
            category=ResourceCategory.TOOL,
            base_abundance=0.4,
            biome_preferences=["mountains", "caves"],
        )

        # Rare resources
        self.resources["gold"] = Resource(
            name="gold",
            category=ResourceCategory.RARE,
            base_abundance=0.1,
            biome_preferences=["caves", "badlands"],
            regeneration_rate=0.0,
        )
        self.resources["diamond"] = Resource(
            name="diamond",
            category=ResourceCategory.RARE,
            base_abundance=0.05,
            biome_preferences=["deep_caves"],
            regeneration_rate=0.0,
        )

        # Luxury/Cultural resources
        self.resources["blue_orchid"] = Resource(
            name="blue_orchid",
            category=ResourceCategory.LUXURY,
            base_abundance=0.15,
            biome_preferences=["swamp", "flower_forest"],
            regeneration_rate=0.02,
        )
        self.resources["rose"] = Resource(
            name="rose",
            category=ResourceCategory.LUXURY,
            base_abundance=0.3,
            biome_preferences=["plains", "flower_forest"],
        )

    def get_abundance(self, resource_name: str, region: Optional[str] = None,
                     biome: Optional[str] = None, season: Optional[str] = None) -> float:
        """
        Get the current abundance of a resource.

        Returns a value from 0-1 indicating how available the resource is.
        """
        if resource_name not in self.resources:
            return 0.0

        resource = self.resources[resource_name]
        abundance = resource.current_abundance

        # Apply regional modifier
        if region and region in self.regional_abundance:
            regional = self.regional_abundance[region].get(resource_name, 1.0)
            abundance *= regional

        # Apply biome modifier
        if biome and resource.biome_preferences:
            if biome in resource.biome_preferences:
                abundance *= 1.5
            else:
                abundance *= 0.5

        # Apply seasonal modifier
        if season and season in resource.seasonal_modifier:
            abundance *= resource.seasonal_modifier[season]

        # Apply active events
        for event in self.active_events:
            if resource_name in event.affected_resources:
                abundance *= event.modifier

        return max(0.0, min(1.0, abundance))

    def consume_resource(self, resource_name: str, amount: float,
                        region: Optional[str] = None) -> bool:
        """
        Record consumption of a resource.

        Returns True if resource was available, False if depleted.
        """
        if resource_name not in self.resources:
            return False

        resource = self.resources[resource_name]
        current = self.get_abundance(resource_name, region)

        if current < 0.1:  # Too scarce to gather
            return False

        # Reduce abundance based on consumption
        depletion = amount * 0.01  # 1% per unit consumed
        resource.current_abundance = max(
            resource.min_abundance,
            resource.current_abundance - depletion
        )

        # Track for regional effects
        if region:
            if region not in self.regional_abundance:
                self.regional_abundance[region] = {}
            current_regional = self.regional_abundance[region].get(resource_name, 1.0)
            self.regional_abundance[region][resource_name] = max(0.1, current_regional - depletion * 2)

        # Track total consumption
        self.consumption_history[resource_name] = \
            self.consumption_history.get(resource_name, 0) + amount

        return True

    def process_day(self, current_day: int) -> list[ScarcityEvent]:
        """
        Process daily resource regeneration and events.

        Returns any new events that occurred.
        """
        new_events = []

        # Regenerate resources
        for resource in self.resources.values():
            if resource.regeneration_rate > 0:
                resource.current_abundance = min(
                    resource.max_abundance,
                    resource.current_abundance + resource.regeneration_rate
                )

        # Regenerate regional abundance
        for region in self.regional_abundance:
            for resource_name in list(self.regional_abundance[region].keys()):
                current = self.regional_abundance[region][resource_name]
                if current < 1.0:
                    resource = self.resources.get(resource_name)
                    if resource and resource.regeneration_rate > 0:
                        self.regional_abundance[region][resource_name] = min(
                            1.0, current + resource.regeneration_rate * 0.5
                        )

        # Update active events
        for event in self.active_events[:]:
            event.days_remaining -= 1
            if event.days_remaining <= 0:
                self.active_events.remove(event)

        # Random events (10% chance per day)
        if random.random() < 0.1:
            event = self._generate_random_event(current_day)
            if event:
                self.active_events.append(event)
                new_events.append(event)

        return new_events

    def _generate_random_event(self, current_day: int) -> Optional[ScarcityEvent]:
        """Generate a random scarcity event."""
        event_types = [
            ("drought", ["wheat", "fish"], 0.5, 3, "A drought has reduced water-dependent resources"),
            ("abundance", ["wheat", "meat"], 1.5, 2, "Favorable conditions have increased food availability"),
            ("ore_discovery", ["iron", "gold"], 1.3, 5, "New ore deposits have been found"),
            ("blight", ["wheat", "wood"], 0.6, 4, "A blight has affected plant resources"),
            ("migration", ["meat", "fish"], 0.7, 3, "Animal migrations have reduced hunting yields"),
        ]

        event_type, resources, modifier, duration, description = random.choice(event_types)

        return ScarcityEvent(
            event_type=event_type,
            affected_resources=resources,
            modifier=modifier,
            duration_days=duration,
            days_remaining=duration,
            description=description,
        )

    def trigger_event(self, event_type: str, resources: list[str],
                     modifier: float, duration: int, description: str) -> ScarcityEvent:
        """Manually trigger a scarcity event."""
        event = ScarcityEvent(
            event_type=event_type,
            affected_resources=resources,
            modifier=modifier,
            duration_days=duration,
            days_remaining=duration,
            description=description,
        )
        self.active_events.append(event)
        return event

    def get_trade_value(self, resource_name: str, region: Optional[str] = None) -> float:
        """
        Calculate trade value based on scarcity.

        Lower abundance = higher value.
        """
        abundance = self.get_abundance(resource_name, region)
        if abundance <= 0:
            return 10.0  # Maximum value for unavailable resources

        # Inverse relationship with abundance
        base_value = 1.0 / abundance

        # Category modifiers
        resource = self.resources.get(resource_name)
        if resource:
            category_multipliers = {
                ResourceCategory.FOOD: 1.0,
                ResourceCategory.BUILDING: 0.8,
                ResourceCategory.TOOL: 1.5,
                ResourceCategory.RARE: 3.0,
                ResourceCategory.LUXURY: 2.0,
            }
            base_value *= category_multipliers.get(resource.category, 1.0)

        return min(10.0, max(0.1, base_value))

    def get_scarcity_report(self, region: Optional[str] = None) -> dict:
        """Get a report of current resource scarcity."""
        report = {
            "abundant": [],  # > 0.7
            "normal": [],    # 0.4 - 0.7
            "scarce": [],    # 0.2 - 0.4
            "critical": [],  # < 0.2
            "active_events": [],
        }

        for resource_name in self.resources:
            abundance = self.get_abundance(resource_name, region)
            if abundance > 0.7:
                report["abundant"].append(resource_name)
            elif abundance > 0.4:
                report["normal"].append(resource_name)
            elif abundance > 0.2:
                report["scarce"].append(resource_name)
            else:
                report["critical"].append(resource_name)

        for event in self.active_events:
            report["active_events"].append({
                "type": event.event_type,
                "description": event.description,
                "days_remaining": event.days_remaining,
            })

        return report
