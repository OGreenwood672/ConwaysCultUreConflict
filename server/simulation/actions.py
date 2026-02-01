"""Actions for Minecraft simulation.

Coordinate system: 2D grid (x, z) - horizontal plane.
All positions are relative to the agent unless otherwise specified.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class SimActionType(Enum):
    """Actions an agent can take in Minecraft."""

    # Movement
    MOVE = "move"              # move(dx, dz) - Walk in direction

    # Communication
    COMMUNICATE = "communicate"  # communicate(target_id, "message")

    # World interaction
    BUILD = "build"            # build(block_type) - Place at current position
    GATHER = "gather"          # gather(dx, dz) - Mine/harvest resource at position
    GIVE = "give"              # give(target_id, item) - Give item to nearby agent

    # Combat
    ATTACK = "attack"          # attack(dx, dz) - Attack entity at position

    # Survival
    EAT = "eat"                # eat(item) - Consume food item from inventory

    # Meta
    IDLE = "idle"              # Do nothing this tick
    DIE = "die"                # Agent death (triggered by game, not chosen)
    ADD_PERSON = "add-person"  # Spawn new agent (system action)


@dataclass
class SimAction:
    """Represents a single action taken by an agent."""

    tick: int
    person_id: int
    action_type: SimActionType

    # Position (for move, gather, attack)
    dx: Optional[int] = None
    dz: Optional[int] = None

    # Target agent (for communicate, give)
    target_id: Optional[int] = None

    # Content (for communicate message, build type, give item, eat item)
    content: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SimAction":
        """Parse action from dict (e.g., from LLM output)."""
        action_str = data.get("action", "idle")
        action_name = action_str.split("(")[0].strip().lower()

        # Handle unknown actions gracefully
        try:
            action_type = SimActionType(action_name)
        except ValueError:
            action_type = SimActionType.IDLE

        return cls(
            tick=data.get("tick", 0),
            person_id=data.get("person_id", 0),
            action_type=action_type,
            dx=data.get("dx"),
            dz=data.get("dz"),
            target_id=data.get("target_id"),
            content=data.get("content"),
        )

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        # Build action string
        if self.action_type == SimActionType.MOVE:
            action_str = f"move({self.dx}, {self.dz})"
        elif self.action_type == SimActionType.COMMUNICATE:
            action_str = f"communicate({self.target_id}, \"{self.content}\")"
        elif self.action_type == SimActionType.BUILD:
            action_str = f"build({self.content})"
        elif self.action_type == SimActionType.GATHER:
            action_str = f"gather({self.dx}, {self.dz})"
        elif self.action_type == SimActionType.GIVE:
            action_str = f"give({self.target_id}, {self.content})"
        elif self.action_type == SimActionType.ATTACK:
            action_str = f"attack({self.dx}, {self.dz})"
        elif self.action_type == SimActionType.EAT:
            action_str = f"eat({self.content})"
        else:
            action_str = self.action_type.value

        result = {
            "tick": self.tick,
            "person_id": self.person_id,
            "action": action_str,
            "action_type": self.action_type.value,
        }

        if self.dx is not None:
            result["dx"] = self.dx
        if self.dz is not None:
            result["dz"] = self.dz
        if self.target_id is not None:
            result["target_id"] = self.target_id
        if self.content is not None:
            result["content"] = self.content

        return result


# Action descriptions for LLM prompts
ACTION_DESCRIPTIONS = {
    SimActionType.MOVE: "move(dx, dz) - Walk in a direction. Examples: move(1, 0) = east, move(-1, 0) = west, move(0, 1) = south, move(0, -1) = north",
    SimActionType.COMMUNICATE: "communicate(target_id, \"message\") - Say something to a specific agent. Example: communicate(3, \"Hello friend\")",
    SimActionType.BUILD: "build(type) - Build at your current position. Types: shelter, wall, marker, chest. Example: build(shelter)",
    SimActionType.GATHER: "gather(dx, dz) - Harvest resource at position. Example: gather(1, 0) gathers from the block to your east",
    SimActionType.GIVE: "give(target_id, item) - Give an item to a nearby agent. Example: give(3, wood)",
    SimActionType.ATTACK: "attack(dx, dz) - Attack entity at position. Example: attack(0, 1) attacks entity to your south",
    SimActionType.EAT: "eat(item) - Eat food from your inventory. Example: eat(bread)",
    SimActionType.IDLE: "idle - Do nothing this tick",
}


def get_available_actions(context: dict = None) -> list[str]:
    """
    Get action descriptions based on context.

    Args:
        context: Optional dict with 'nearby_agents', 'nearby_resources', 'inventory', 'threats'

    Returns:
        List of action description strings for LLM prompt
    """
    actions = []

    # Movement always available
    actions.append(ACTION_DESCRIPTIONS[SimActionType.MOVE])

    # Communication if agents nearby
    if context and context.get("nearby_agents"):
        actions.append(ACTION_DESCRIPTIONS[SimActionType.COMMUNICATE])

    # Gathering if resources nearby
    if context and context.get("nearby_resources"):
        actions.append(ACTION_DESCRIPTIONS[SimActionType.GATHER])

    # Building always available
    actions.append(ACTION_DESCRIPTIONS[SimActionType.BUILD])

    # Giving if agents nearby and have inventory
    if context and context.get("nearby_agents") and context.get("inventory"):
        actions.append(ACTION_DESCRIPTIONS[SimActionType.GIVE])

    # Attack if threats nearby
    if context and context.get("threats"):
        actions.append(ACTION_DESCRIPTIONS[SimActionType.ATTACK])

    # Eating if have food
    if context and context.get("has_food"):
        actions.append(ACTION_DESCRIPTIONS[SimActionType.EAT])

    # Idle always available
    actions.append(ACTION_DESCRIPTIONS[SimActionType.IDLE])

    return actions
