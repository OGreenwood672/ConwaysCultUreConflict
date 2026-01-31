#!/usr/bin/env python3
"""
Test script for Bedrock LLM integration with full agent context.

Uses existing agents:
- agent_001: "The Builder"
- agent_002: "The Seeker"
- agent_003: "The Merchant"

Runs 3 ticks with full context injection and prints actions + reasoning.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # noqa: E402

from simulation.interface import SimulationInterface, PERSON_TO_AGENT
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_test_world_state(tick: int) -> list[dict]:
    """Create mock world state for testing."""
    return [
        {
            "id": 0,
            "culture": 0,
            "x": 10 + tick,
            "y": 20,
            "health": 85,
            "hunger": 30,
            "nearby": ["agent_002 at (12, 20)", "tree at (11, 21)"],
        },
        {
            "id": 1,
            "culture": 1,
            "x": 12,
            "y": 20,
            "health": 90,
            "hunger": 25,
            "nearby": ["agent_001 at (10, 20)", "stone at (13, 19)"],
        },
        {
            "id": 2,
            "culture": 0,
            "x": 5,
            "y": 5,
            "health": 95,
            "hunger": 15,
            "nearby": ["chest at (6, 5)", "crafting_table at (4, 5)"],
        },
    ]


def run_test(use_mock: bool = False, num_ticks: int = 3, end_day: bool = False):
    """Run the Bedrock simulation test."""
    print("=" * 60)
    print(f"Bedrock Simulation Test ({'MOCK' if use_mock else 'REAL LLM'})")
    print("=" * 60)
    print()

    # Initialize simulation
    sim = SimulationInterface(use_mock_llm=use_mock, world_path="world")

    # Create starting state
    start_state = [
        {"id": 0, "culture": 0},  # The Builder
        {"id": 1, "culture": 1},  # The Seeker
        {"id": 2, "culture": 0},  # The Merchant
    ]

    sim.initialize(start_state)

    # Print agent mapping
    print("Agent Mapping:")
    for person_id, agent_id in PERSON_TO_AGENT.items():
        soul = sim._souls.get(agent_id)
        name = soul.name if soul else "Unknown"
        print(f"  Person {person_id} -> {agent_id} ({name})")
    print()

    # Run ticks
    for tick in range(num_ticks):
        print(f"Tick {tick}:")
        print("-" * 40)

        world_state = create_test_world_state(tick)
        actions = sim.process_tick(tick, world_state)

        for action in actions:
            person_id = action.to_dict()["person_id"]
            agent_id = PERSON_TO_AGENT.get(person_id, "unknown")
            culture = world_state[person_id]["culture"]

            # Get full LLM decision JSON
            decision = sim.get_last_decision(person_id)

            print(f"  Person {person_id} ({agent_id}, culture {culture}):")
            print(f"    LLM Decision: {decision}")
            print(f"    SimAction: {action}")

        print()

    # End day and update culture
    if end_day:
        print("=" * 60)
        print("Ending day - updating culture.md...")
        print("=" * 60)
        result = sim.end_day(culture_id="alpha")
        print(f"Events processed: {result['events_processed']}")
        print(f"New day: {result.get('day', 'N/A')}")
        if result.get("culture_update"):
            print()
            print("Updated culture.md:")
            print("-" * 40)
            print(
                result["culture_update"][:500] + "..."
                if len(result.get("culture_update", "")) > 500
                else result["culture_update"]
            )
        print()

    print("=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Bedrock LLM integration")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM instead of real Bedrock (default: use real LLM)",
    )
    parser.add_argument(
        "--ticks", type=int, default=3, help="Number of ticks to run (default: 3)"
    )
    parser.add_argument(
        "--end-day",
        action="store_true",
        help="End the day and update culture.md based on events",
    )

    args = parser.parse_args()

    # Change to project root for correct world path
    import os

    os.chdir(Path(__file__).parent.parent.parent)

    run_test(use_mock=args.mock, num_ticks=args.ticks, end_day=args.end_day)
