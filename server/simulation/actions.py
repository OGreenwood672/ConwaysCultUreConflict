from enum import Enum
from dataclasses import dataclass
from typing import Optional


class SimActionType(Enum):
    MOVE = "move"
    ADD_PERSON = "add-person"
    DIE = "die"
    COMMUNICATE = "communicate"
    BUILD = "build"
    IDLE = "idle"


@dataclass
class SimAction:
    tick: int
    person_id: int
    action_type: SimActionType
    x: Optional[int] = None
    y: Optional[int] = None
    target: Optional[str] = None  # For build action

    def to_dict(self) -> dict:
        action_str = self.action_type.value
        if self.action_type == SimActionType.MOVE:
            action_str = f"move({self.x}, {self.y})"
        elif self.action_type == SimActionType.COMMUNICATE:
            action_str = f"communicate({self.x}, {self.y})"
        elif self.action_type == SimActionType.BUILD:
            action_str = f"build({self.target})"

        return {
            "tick": self.tick,
            "person_id": self.person_id,
            "action": action_str
        }
