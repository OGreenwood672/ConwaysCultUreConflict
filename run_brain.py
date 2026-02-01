#!/usr/bin/env python3
"""Run the AI Brain Service."""

import asyncio
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from brain import BrainService


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Brain Service")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM client (for testing)")
    parser.add_argument("--world", default="world", help="Path to world directory")
    parser.add_argument("--output", default="output", help="Path to output directory")
    parser.add_argument("--culture", default="alpha", help="Culture ID to use")
    args = parser.parse_args()

    print("=" * 50)
    print("AI Brain Service")
    print("=" * 50)
    print(f"World path: {args.world}")
    print(f"Output dir: {args.output}")
    print(f"Culture ID: {args.culture}")
    print(f"Mock LLM:   {args.mock}")
    print("=" * 50)

    brain = BrainService(
        world_path=args.world,
        output_dir=args.output,
        use_mock_llm=args.mock,
        culture_id=args.culture
    )

    try:
        await brain.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        brain.stop()


if __name__ == "__main__":
    asyncio.run(main())
