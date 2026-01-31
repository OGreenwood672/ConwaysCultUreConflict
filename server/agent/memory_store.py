"""Memory store - storage and retrieval of agent memories."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from .memory import Memory, MemoryType
from logger import logger


class MemoryStore:
    """
    Stores and retrieves memories for agents.

    Implements the retrieval scoring from Stanford Generative Agents:
    score = recency * 0.3 + importance * 0.3 + relevance * 0.4

    Memories are persisted to JSON files per agent.
    """

    def __init__(self, world_path: str = "world"):
        self.world_path = Path(world_path)
        self._memories: dict[str, list[Memory]] = {}  # agent_id -> memories

    def _get_memory_file(self, agent_id: str) -> Path:
        """Get the path to an agent's memory file."""
        return self.world_path / "agents" / agent_id / "memories.json"

    def load_memories(self, agent_id: str) -> list[Memory]:
        """Load all memories for an agent from disk."""
        if agent_id in self._memories:
            return self._memories[agent_id]

        memory_file = self._get_memory_file(agent_id)
        if not memory_file.exists():
            self._memories[agent_id] = []
            return []

        with open(memory_file, "r") as f:
            data = json.load(f)

        memories = [Memory.from_dict(m) for m in data]
        self._memories[agent_id] = memories
        return memories

    def save_memories(self, agent_id: str) -> None:
        """Save all memories for an agent to disk."""
        memories = self._memories.get(agent_id, [])
        memory_file = self._get_memory_file(agent_id)
        memory_file.parent.mkdir(parents=True, exist_ok=True)

        data = [m.to_dict() for m in memories]
        with open(memory_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.file_write(str(memory_file))

    def add_memory(self, memory: Memory, persist: bool = True) -> None:
        """Add a memory to the store."""
        agent_id = memory.agent_id
        if agent_id not in self._memories:
            self.load_memories(agent_id)

        self._memories[agent_id].append(memory)
        logger.memory_add(agent_id, memory.memory_type.value, memory.content)

        if persist:
            self.save_memories(agent_id)

    def get_memory_by_id(self, agent_id: str, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory by ID."""
        memories = self.load_memories(agent_id)
        for memory in memories:
            if memory.id == memory_id:
                return memory
        return None

    def get_memories_by_type(self, agent_id: str,
                            memory_type: MemoryType) -> list[Memory]:
        """Get all memories of a specific type."""
        memories = self.load_memories(agent_id)
        return [m for m in memories if m.memory_type == memory_type]

    def get_recent_memories(self, agent_id: str, count: int = 10,
                           memory_type: Optional[MemoryType] = None) -> list[Memory]:
        """Get the most recent memories."""
        memories = self.load_memories(agent_id)

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:count]

    def get_memories_by_day(self, agent_id: str, game_day: int) -> list[Memory]:
        """Get all memories from a specific game day."""
        memories = self.load_memories(agent_id)
        return [m for m in memories if m.game_day == game_day]

    def get_memories_involving_agent(self, agent_id: str,
                                     other_agent_id: str) -> list[Memory]:
        """Get all memories involving another agent."""
        memories = self.load_memories(agent_id)
        return [m for m in memories if other_agent_id in m.involved_agents]

    def calculate_retrieval_score(self, memory: Memory,
                                  query_embedding: Optional[list[float]] = None,
                                  current_time: Optional[datetime] = None) -> float:
        """
        Calculate retrieval score for a memory.

        score = recency * 0.3 + importance * 0.3 + relevance * 0.4

        If no embedding is provided, relevance is treated as 0.5 (neutral).
        """
        recency = memory.calculate_recency_score(current_time)
        importance = memory.calculate_importance_score()

        # Calculate relevance from embedding similarity if available
        if query_embedding and memory.embedding:
            relevance = self._cosine_similarity(query_embedding, memory.embedding)
        else:
            relevance = 0.5  # Neutral relevance without embeddings

        return recency * 0.3 + importance * 0.3 + relevance * 0.4

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    def retrieve_relevant_memories(self, agent_id: str,
                                   query_embedding: Optional[list[float]] = None,
                                   count: int = 10,
                                   memory_types: Optional[list[MemoryType]] = None,
                                   current_time: Optional[datetime] = None) -> list[Memory]:
        """
        Retrieve the most relevant memories for a query.

        Uses the Stanford Generative Agents scoring formula:
        score = recency * 0.3 + importance * 0.3 + relevance * 0.4
        """
        memories = self.load_memories(agent_id)

        if memory_types:
            memories = [m for m in memories if m.memory_type in memory_types]

        # Score all memories
        scored = []
        for memory in memories:
            score = self.calculate_retrieval_score(memory, query_embedding, current_time)
            scored.append((score, memory))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top memories and mark as accessed
        result = []
        for _, memory in scored[:count]:
            memory.mark_accessed()
            result.append(memory)

        return result

    def get_unreflected_observations(self, agent_id: str,
                                     importance_threshold: float = 3.0) -> list[Memory]:
        """
        Get observations that haven't been processed into reflections.

        Returns observations whose cumulative importance exceeds the threshold.
        """
        memories = self.load_memories(agent_id)

        # Get all observations
        observations = [m for m in memories if m.memory_type == MemoryType.OBSERVATION]

        # Get IDs of observations that have been reflected on
        reflected_ids = set()
        for memory in memories:
            if memory.memory_type == MemoryType.REFLECTION:
                reflected_ids.update(memory.source_memory_ids)

        # Filter to unreflected observations
        unreflected = [o for o in observations if o.id not in reflected_ids]

        # Sort by timestamp
        unreflected.sort(key=lambda m: m.timestamp)

        # Return if cumulative importance exceeds threshold
        cumulative = sum(o.importance for o in unreflected)
        if cumulative >= importance_threshold:
            return unreflected

        return []

    def get_all_beliefs(self, agent_id: str) -> list[Memory]:
        """Get all current beliefs for an agent."""
        return self.get_memories_by_type(agent_id, MemoryType.BELIEF)

    def count_memories(self, agent_id: str) -> dict[str, int]:
        """Get counts of memories by type."""
        memories = self.load_memories(agent_id)
        counts = {
            "total": len(memories),
            "observations": 0,
            "reflections": 0,
            "beliefs": 0,
            "plans": 0,
        }
        for memory in memories:
            if memory.memory_type == MemoryType.OBSERVATION:
                counts["observations"] += 1
            elif memory.memory_type == MemoryType.REFLECTION:
                counts["reflections"] += 1
            elif memory.memory_type == MemoryType.BELIEF:
                counts["beliefs"] += 1
            elif memory.memory_type == MemoryType.PLAN:
                counts["plans"] += 1

        return counts

    def clear_memories(self, agent_id: str) -> None:
        """Clear all memories for an agent (use with caution)."""
        self._memories[agent_id] = []
        memory_file = self._get_memory_file(agent_id)
        if memory_file.exists():
            memory_file.unlink()
