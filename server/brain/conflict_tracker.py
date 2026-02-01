"""Conflict tracker - monitors wars and updates .md files with conflict information."""

import json
from datetime import datetime
from pathlib import Path


class ConflictTracker:
    """
    Tracks wars, battles, and casualties between cultures.
    Updates culture.md and agent status.md files with conflict information.
    """

    def __init__(self, world_path: str = "world", output_dir: str = "output"):
        self.world_path = Path(world_path)
        self.output_dir = Path(output_dir)
        self.game_state_file = self.output_dir / "game_state.json"

        # Track state
        self._last_wars = set()
        self._last_kill_counts = {}

    def update_from_game_state(self) -> dict:
        """Read game state and update .md files with conflict info."""
        if not self.game_state_file.exists():
            return {}

        try:
            with open(self.game_state_file) as f:
                state = json.load(f)
        except Exception as e:
            print(f"[Conflict] Error reading game state: {e}")
            return {}

        conflicts = state.get("conflicts", {})
        if not conflicts:
            return {}

        updates = {
            "wars_updated": [],
            "agents_updated": [],
            "events_logged": 0
        }

        # Update culture files with war status
        for war in conflicts.get("activeWars", []):
            cultures = war.get("cultures", [])
            if len(cultures) == 2:
                self._update_culture_war_status(cultures[0], cultures[1], war)
                self._update_culture_war_status(cultures[1], cultures[0], war)
                updates["wars_updated"].extend(cultures)

        # Update agent status files with combat stats
        for agent_id, stats in conflicts.get("killCounts", {}).items():
            if stats != self._last_kill_counts.get(agent_id):
                self._update_agent_combat_status(agent_id, stats, state.get("agents", {}).get(agent_id, {}))
                updates["agents_updated"].append(agent_id)
                self._last_kill_counts[agent_id] = stats.copy()

        # Log recent conflict events
        events = conflicts.get("recentEvents", [])
        updates["events_logged"] = len(events)

        return updates

    def _update_culture_war_status(self, culture_id: str, enemy_culture: str, war: dict):
        """Update a culture's .md file with war information."""
        culture_file = self.world_path / "cultures" / culture_id / "culture.md"
        if not culture_file.exists():
            return

        content = culture_file.read_text()

        # Check if war section exists
        war_section = f"\n## Active Conflicts\n"

        if "## Active Conflicts" not in content:
            # Add war section
            content += f"\n{war_section}"

        # Build war info
        kills = war.get("kills", {})
        our_kills = kills.get(culture_id, 0)
        enemy_kills = kills.get(enemy_culture, 0)
        reason = war.get("reason", "Unknown")
        battles = war.get("battleCount", 0)
        start_time = war.get("startTime", 0)

        # Calculate war duration
        if start_time:
            duration_ms = datetime.now().timestamp() * 1000 - start_time
            duration_min = int(duration_ms / 60000)
        else:
            duration_min = 0

        war_entry = f"""
### War with {enemy_culture.title()}
- **Status**: ACTIVE
- **Reason**: {reason}
- **Duration**: {duration_min} minutes
- **Our Kills**: {our_kills}
- **Our Losses**: {enemy_kills}
- **Battles**: {battles}
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Replace or append war entry
        war_marker = f"### War with {enemy_culture.title()}"
        if war_marker in content:
            # Find and replace existing section
            start_idx = content.find(war_marker)
            # Find the next ### or end of file
            next_section = content.find("\n### ", start_idx + 1)
            next_h2 = content.find("\n## ", start_idx + 1)

            if next_section == -1:
                next_section = len(content)
            if next_h2 != -1 and next_h2 < next_section:
                next_section = next_h2

            content = content[:start_idx] + war_entry.strip() + "\n" + content[next_section:]
        else:
            # Append after Active Conflicts header
            idx = content.find("## Active Conflicts")
            if idx != -1:
                insert_point = content.find("\n", idx) + 1
                content = content[:insert_point] + war_entry + content[insert_point:]

        culture_file.write_text(content)

    def _update_agent_combat_status(self, agent_id: str, stats: dict, agent_state: dict):
        """Update an agent's status.md file with combat information."""
        status_file = self.world_path / "agents" / agent_id / "status.md"

        # Create status file if it doesn't exist
        if not status_file.exists():
            status_file.parent.mkdir(parents=True, exist_ok=True)
            status_file.write_text(f"# {agent_id} Status\n\n")

        content = status_file.read_text()

        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        kd_ratio = kills / max(deaths, 1)

        # Determine combat rank
        if kills >= 10:
            rank = "Veteran Warrior"
        elif kills >= 5:
            rank = "Blooded Fighter"
        elif kills >= 1:
            rank = "Combatant"
        else:
            rank = "Untested"

        combat_section = f"""
## Combat Record
- **Kills**: {kills}
- **Deaths**: {deaths}
- **K/D Ratio**: {kd_ratio:.2f}
- **Combat Rank**: {rank}
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Add position if available
        if agent_state.get("position"):
            pos = agent_state["position"]
            combat_section += f"- **Last Position**: ({pos.get('x', 0)}, {pos.get('y', 0)}, {pos.get('z', 0)})\n"

        # Replace or append combat section
        if "## Combat Record" in content:
            start_idx = content.find("## Combat Record")
            next_section = content.find("\n## ", start_idx + 1)
            if next_section == -1:
                next_section = len(content)
            content = content[:start_idx] + combat_section.strip() + "\n" + content[next_section:]
        else:
            content += combat_section

        status_file.write_text(content)

    def log_major_event(self, event_type: str, details: dict):
        """Log a major conflict event to the world history."""
        history_file = self.world_path / "history.md"

        if not history_file.exists():
            history_file.write_text("# World History\n\nA chronicle of major events.\n\n## Events\n\n")

        content = history_file.read_text()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if event_type == "WAR_DECLARED":
            cultures = details.get("cultures", ["Unknown", "Unknown"])
            reason = details.get("reason", "Unknown")
            entry = f"- **[{timestamp}]** WAR DECLARED: {cultures[0].title()} vs {cultures[1].title()} - {reason}\n"
        elif event_type == "KILL":
            killer = details.get("killer", {})
            victim = details.get("victim", {})
            entry = f"- **[{timestamp}]** BATTLE: {killer.get('id', 'Unknown')} ({killer.get('culture', '?')}) slew {victim.get('id', 'Unknown')} ({victim.get('culture', '?')})\n"
        else:
            entry = f"- **[{timestamp}]** {event_type}: {json.dumps(details)}\n"

        # Insert after "## Events" header
        idx = content.find("## Events")
        if idx != -1:
            insert_point = content.find("\n", idx) + 1
            content = content[:insert_point] + entry + content[insert_point:]
        else:
            content += f"\n## Events\n\n{entry}"

        history_file.write_text(content)


def update_conflicts(world_path: str = "world", output_dir: str = "output"):
    """Convenience function to update conflict information."""
    tracker = ConflictTracker(world_path, output_dir)
    return tracker.update_from_game_state()
