"""Output writer - writes JSON files for Mineflayer to read."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from .phase_generator import AgentPhase
from .dialogue_generator import DialoguePool, Dialogue


class OutputWriter:
    """
    Writes output files for Mineflayer to consume.

    Generates:
    - phases.json: Current phase per agent
    - dialogue_pool.json: Pre-generated conversations
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_phases(self, phases: dict[str, AgentPhase]) -> Path:
        """
        Write phases.json file.

        Args:
            phases: Dict of agent_id -> AgentPhase

        Returns:
            Path to written file
        """
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agents": {}
        }

        for agent_id, phase in phases.items():
            output["agents"][agent_id] = {
                "phase": phase.phase.value,
                "target": phase.target,
                "priority": phase.priority,
                "reasoning": phase.reasoning
            }

        output_path = self.output_dir / "phases.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        return output_path

    def write_dialogues(self, pool: DialoguePool) -> Path:
        """
        Write dialogue_pool.json file.

        Args:
            pool: DialoguePool with pre-generated conversations

        Returns:
            Path to written file
        """
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "culture_context": pool.culture_context,
            "dialogues": []
        }

        for dialogue in pool.dialogues:
            output["dialogues"].append({
                "id": dialogue.id,
                "participants": dialogue.participants,
                "context": dialogue.context,
                "lines": [
                    {"speaker": line.speaker, "text": line.text}
                    for line in dialogue.lines
                ],
                "used": dialogue.used
            })

        output_path = self.output_dir / "dialogue_pool.json"
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        return output_path

    def read_phases(self) -> Optional[dict]:
        """Read current phases.json if it exists."""
        phases_path = self.output_dir / "phases.json"
        if not phases_path.exists():
            return None

        with open(phases_path, "r") as f:
            return json.load(f)

    def read_dialogues(self) -> Optional[dict]:
        """Read current dialogue_pool.json if it exists."""
        pool_path = self.output_dir / "dialogue_pool.json"
        if not pool_path.exists():
            return None

        with open(pool_path, "r") as f:
            return json.load(f)

    def mark_dialogue_used(self, dialogue_id: str) -> bool:
        """
        Mark a dialogue as used in the pool.

        Returns True if successful, False if dialogue not found.
        """
        pool_path = self.output_dir / "dialogue_pool.json"
        if not pool_path.exists():
            return False

        with open(pool_path, "r") as f:
            data = json.load(f)

        found = False
        for dialogue in data["dialogues"]:
            if dialogue["id"] == dialogue_id:
                dialogue["used"] = True
                found = True
                break

        if found:
            with open(pool_path, "w") as f:
                json.dump(data, f, indent=2)

        return found

    def get_unused_dialogue_count(self) -> int:
        """Get count of unused dialogues in pool."""
        data = self.read_dialogues()
        if not data:
            return 0

        return sum(1 for d in data["dialogues"] if not d["used"])

    def get_output_status(self) -> dict:
        """Get status of output files."""
        phases_path = self.output_dir / "phases.json"
        dialogues_path = self.output_dir / "dialogue_pool.json"

        status = {
            "phases_exists": phases_path.exists(),
            "dialogues_exists": dialogues_path.exists(),
            "phases_timestamp": None,
            "dialogues_timestamp": None,
            "agent_count": 0,
            "unused_dialogues": 0
        }

        if phases_path.exists():
            data = self.read_phases()
            status["phases_timestamp"] = data.get("timestamp")
            status["agent_count"] = len(data.get("agents", {}))

        if dialogues_path.exists():
            data = self.read_dialogues()
            status["dialogues_timestamp"] = data.get("timestamp")
            status["unused_dialogues"] = sum(
                1 for d in data.get("dialogues", []) if not d["used"]
            )

        return status
