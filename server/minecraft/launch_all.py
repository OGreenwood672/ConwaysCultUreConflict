#!/usr/bin/env python3
"""
Launch all 25 Minecraft agents with their cultures and personalities.
"""

import json
import subprocess
import time
import os
import signal
import sys
from pathlib import Path


def load_soul_from_file(agent_id: str, world_path: str = "world") -> str:
    """Load soul.md content for an agent."""
    soul_path = Path(world_path) / "agents" / agent_id / "soul.md"
    if soul_path.exists():
        return soul_path.read_text()
    return f"# {agent_id}\n\nNo soul defined yet."


def generate_system_prompt_from_soul(agent_id: str, soul_content: str) -> str:
    """Generate system prompt using existing soul.md content."""
    return f"""You are {agent_id}, an autonomous agent in Minecraft.

## Your Identity
{soul_content}

## How to Play

You control a Minecraft bot. Send JSON commands to act:

### Movement
- Move to coordinates: {{"action": "move", "x": 100, "y": 64, "z": 100}}
- Move relative: {{"action": "move_relative", "dx": 5, "dy": 0, "dz": 0}}

### Communication
- Public chat: {{"action": "chat", "message": "Hello everyone!"}}
- Whisper: {{"action": "whisper", "to": "Ironhand", "message": "Private message"}}

### Observation
- Get status: {{"action": "get_status"}}
- See nearby players: {{"action": "get_nearby_players"}}
- See nearby blocks: {{"action": "get_nearby_blocks"}}
- Check inventory: {{"action": "get_inventory"}}

### Actions
- Dig block: {{"action": "dig", "x": 10, "y": 64, "z": 10}}
- Attack: {{"action": "attack", "target": "Zombie"}}
- Stop: {{"action": "stop"}}

## Behavior
1. Act according to your soul/personality
2. Cooperate with your culture, be strategic with others
3. Communicate to coordinate
4. React to events and other agents

Start by checking your surroundings with get_status and get_nearby_players.
"""


def generate_system_prompt(agent: dict, cultures: dict, types: dict) -> str:
    """Generate a system prompt for an agent based on their culture and type."""
    culture = cultures[agent["culture"]]
    agent_type = types[agent["type"]]

    return f"""You are {agent["name"]}, a {agent["type"]} of the {culture["name"]} culture.

## Your Identity
- **Name**: {agent["name"]}
- **Role**: {agent["type"].title()}
- **Culture**: {culture["name"]}
- **Culture Values**: {", ".join(culture["values"])}

## Your Personality
- **Traits**: {", ".join(agent_type["traits"])}
- **Skills**: {", ".join(agent_type["skills"])}
- **Goals**: {", ".join(agent_type["goals"])}

## How to Play

You control a Minecraft bot. Send JSON commands to stdin to act:

### Movement
- Move to coordinates: {{"action": "move", "x": 100, "y": 64, "z": 100}}
- Move relative: {{"action": "move_relative", "dx": 5, "dy": 0, "dz": 0}}

### Communication
- Public chat: {{"action": "chat", "message": "Hello everyone!"}}
- Whisper to agent: {{"action": "whisper", "to": "Mason", "message": "Private message"}}

### Observation
- Get your status: {{"action": "get_status"}}
- See nearby players: {{"action": "get_nearby_players"}}
- See nearby blocks: {{"action": "get_nearby_blocks"}}
- Check inventory: {{"action": "get_inventory"}}

### Actions
- Dig block: {{"action": "dig", "x": 10, "y": 64, "z": 10}}
- Attack entity: {{"action": "attack", "target": "Zombie"}}
- Stop moving: {{"action": "stop"}}

## Your Culture's Territory
Your people spawn near coordinates ({culture["spawn_area"]["x"]}, {culture["spawn_area"]["z"]}).

## Other Cultures
- **The Builders (Alpha)**: Value construction and order
- **The Wanderers (Beta)**: Value exploration and freedom
- **The Collective (Gamma)**: Value community and tradition

## Behavior Guidelines
1. Act according to your personality and goals
2. Cooperate with your culture, be wary of others
3. Communicate to coordinate with allies
4. Pursue your type-specific objectives
5. React to events and other agents

Start by checking your surroundings with get_status and get_nearby_players.
"""


def load_config():
    config_path = Path(__file__).parent / "agents_config.json"
    with open(config_path) as f:
        return json.load(f)


def discover_agents(world_path: str = "world") -> list[dict]:
    """Discover agents from world/agents/ directory."""
    agents_dir = Path(world_path) / "agents"
    agents = []

    for agent_dir in sorted(agents_dir.iterdir()):
        if agent_dir.is_dir():
            soul_path = agent_dir / "soul.md"
            if soul_path.exists():
                soul_content = soul_path.read_text()
                # Extract name from first line: # agent_id - "Name"
                first_line = soul_content.split("\n")[0]
                if '"' in first_line:
                    name = first_line.split('"')[1]
                else:
                    name = agent_dir.name

                # Extract culture from metadata
                culture = "unknown"
                if "culture_id:" in soul_content:
                    for line in soul_content.split("\n"):
                        if "culture_id:" in line:
                            culture = line.split(":")[1].strip()
                            break

                agents.append({
                    "id": agent_dir.name,
                    "name": name,
                    "culture": culture,
                    "soul": soul_content
                })

    return agents


class AgentLauncher:
    def __init__(self, host: str = "localhost", port: int = 25565, world_path: str = "world"):
        self.host = host
        self.port = port
        self.world_path = world_path
        self.processes: dict[str, subprocess.Popen] = {}
        self.config = load_config()

    def spawn_agent(self, agent: dict, delay: float = 0.5) -> subprocess.Popen:
        """Spawn a single agent bot."""
        prompt = generate_system_prompt(
            agent,
            self.config["cultures"],
            self.config["types"]
        )

        # Write prompt to temp file
        prompt_file = Path(f"/tmp/mc_prompt_{agent['id']}.txt")
        prompt_file.write_text(prompt)

        env = os.environ.copy()
        env.update({
            "MC_HOST": self.host,
            "MC_PORT": str(self.port),
            "MC_USERNAME": agent["name"]
        })

        bot_script = Path(__file__).parent / "bot.js"

        proc = subprocess.Popen(
            ["node", str(bot_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )

        self.processes[agent["id"]] = proc
        print(f"[{agent['name']}] Spawned ({agent['culture']}/{agent['type']})")

        time.sleep(delay)  # Stagger spawns to avoid overwhelming server
        return proc

    def spawn_all(self, delay: float = 0.5):
        """Spawn all agents from config."""
        agents = self.config["agents"]
        print(f"Spawning {len(agents)} agents from config...")
        print("=" * 50)

        for agent in agents:
            try:
                self.spawn_agent(agent, delay)
            except Exception as e:
                print(f"[{agent['name']}] Failed to spawn: {e}")

        print("=" * 50)
        print(f"Spawned {len(self.processes)} agents")

    def spawn_from_world(self, delay: float = 0.5):
        """Spawn all agents discovered from world/agents/ directory."""
        agents = discover_agents(self.world_path)
        print(f"Spawning {len(agents)} agents from {self.world_path}/agents/...")
        print("=" * 50)

        for agent in agents:
            try:
                self.spawn_agent_from_soul(agent, delay)
            except Exception as e:
                print(f"[{agent['name']}] Failed to spawn: {e}")

        print("=" * 50)
        print(f"Spawned {len(self.processes)} agents")

    def spawn_agent_from_soul(self, agent: dict, delay: float = 0.5) -> subprocess.Popen:
        """Spawn an agent using their soul.md content."""
        prompt = generate_system_prompt_from_soul(agent["id"], agent["soul"])

        # Write prompt to temp file
        prompt_file = Path(f"/tmp/mc_prompt_{agent['id']}.txt")
        prompt_file.write_text(prompt)

        env = os.environ.copy()
        env.update({
            "MC_HOST": self.host,
            "MC_PORT": str(self.port),
            "MC_USERNAME": agent["name"]
        })

        bot_script = Path(__file__).parent / "bot.js"

        proc = subprocess.Popen(
            ["node", str(bot_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )

        self.processes[agent["id"]] = proc
        print(f"[{agent['name']}] Spawned ({agent['culture']})")

        time.sleep(delay)
        return proc

    def spawn_culture(self, culture_id: str, delay: float = 0.5):
        """Spawn all agents from a specific culture."""
        agents = [a for a in self.config["agents"] if a["culture"] == culture_id]
        print(f"Spawning {len(agents)} agents from {culture_id}...")

        for agent in agents:
            try:
                self.spawn_agent(agent, delay)
            except Exception as e:
                print(f"[{agent['name']}] Failed to spawn: {e}")

    def get_status(self):
        """Get status of all running agents."""
        alive = 0
        dead = 0
        for agent_id, proc in self.processes.items():
            if proc.poll() is None:
                alive += 1
            else:
                dead += 1
        return {"alive": alive, "dead": dead, "total": len(self.processes)}

    def stop_all(self):
        """Stop all agent processes."""
        print("Stopping all agents...")
        for agent_id, proc in self.processes.items():
            proc.terminate()
        time.sleep(1)
        for agent_id, proc in self.processes.items():
            if proc.poll() is None:
                proc.kill()
        self.processes.clear()
        print("All agents stopped")

    def send_command(self, agent_id: str, command: dict):
        """Send a command to a specific agent."""
        proc = self.processes.get(agent_id)
        if proc and proc.poll() is None:
            proc.stdin.write(json.dumps(command) + "\n")
            proc.stdin.flush()
            return True
        return False

    def broadcast_chat(self, message: str):
        """Make all agents say something."""
        for agent_id in self.processes:
            self.send_command(agent_id, {"action": "chat", "message": message})


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Launch Minecraft agents")
    parser.add_argument("--host", default="localhost", help="Minecraft server host")
    parser.add_argument("--port", type=int, default=25565, help="Minecraft server port")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between spawns (seconds)")
    parser.add_argument("--culture", help="Only spawn agents from this culture")
    parser.add_argument("--list", action="store_true", help="List all agents and exit")
    parser.add_argument("--from-world", action="store_true", help="Load agents from world/agents/ soul.md files")
    parser.add_argument("--world-path", default="world", help="Path to world directory")

    args = parser.parse_args()

    if args.from_world or args.list:
        # Discover agents from world directory
        agents = discover_agents(args.world_path)

        if args.list:
            print(f"\nAgents in {args.world_path}/agents/:")
            print("=" * 60)

            # Group by culture
            cultures = {}
            for a in agents:
                c = a["culture"]
                if c not in cultures:
                    cultures[c] = []
                cultures[c].append(a)

            for culture, culture_agents in sorted(cultures.items()):
                print(f"\n{culture.title()} - {len(culture_agents)} agents")
                for a in culture_agents:
                    print(f"  - {a['name']} ({a['id']})")

            print(f"\nTotal: {len(agents)} agents")
            return

    else:
        config = load_config()

        if args.list:
            print("\nConfigured Agents (from agents_config.json):")
            print("=" * 60)
            for culture_id, culture in config["cultures"].items():
                culture_agents = [a for a in config["agents"] if a["culture"] == culture_id]
                print(f"\n{culture['name']} ({culture_id}) - {len(culture_agents)} agents")
                print(f"  Values: {', '.join(culture['values'])}")
                print(f"  Spawn: ({culture['spawn_area']['x']}, {culture['spawn_area']['z']})")
                print("  Agents:")
                for a in culture_agents:
                    print(f"    - {a['name']} ({a['type']})")
            return

    launcher = AgentLauncher(args.host, args.port, args.world_path)

    def signal_handler(sig, frame):
        print("\nReceived shutdown signal...")
        launcher.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.from_world:
            launcher.spawn_from_world(args.delay)
        elif args.culture:
            launcher.spawn_culture(args.culture, args.delay)
        else:
            launcher.spawn_all(args.delay)

        print("\nAgents are running. Press Ctrl+C to stop.")
        print("Status updates every 10 seconds:\n")

        while True:
            time.sleep(10)
            status = launcher.get_status()
            print(f"Status: {status['alive']}/{status['total']} agents alive")

    except KeyboardInterrupt:
        pass
    finally:
        launcher.stop_all()


if __name__ == "__main__":
    main()
