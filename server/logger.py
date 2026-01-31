"""Simple CLI logger with colors for simulation events."""

import sys
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    TICK = "tick"
    DECISION = "decision"
    LLM = "llm"
    MEMORY = "memory"
    REFLECTION = "reflection"
    CULTURE = "culture"
    FILE = "file"
    ERROR = "error"


# ANSI colors
COLORS = {
    LogLevel.TICK: "\033[90m",       # Gray
    LogLevel.DECISION: "\033[92m",   # Green
    LogLevel.LLM: "\033[94m",        # Blue
    LogLevel.MEMORY: "\033[93m",     # Yellow
    LogLevel.REFLECTION: "\033[95m", # Magenta
    LogLevel.CULTURE: "\033[96m",    # Cyan
    LogLevel.FILE: "\033[33m",       # Orange
    LogLevel.ERROR: "\033[91m",      # Red
}
RESET = "\033[0m"
BOLD = "\033[1m"


class SimulationLogger:
    """Logger for simulation events with colored output."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.tick_count = 0

    def _format(self, level: LogLevel, message: str, agent_id: str = None) -> str:
        """Format a log message with color and timestamp."""
        color = COLORS.get(level, "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{level.value.upper():10}]"
        agent = f" [{agent_id}]" if agent_id else ""
        return f"{color}{timestamp} {prefix}{agent} {message}{RESET}"

    def log(self, level: LogLevel, message: str, agent_id: str = None) -> None:
        """Log a message."""
        if not self.verbose and level == LogLevel.TICK:
            return
        print(self._format(level, message, agent_id), file=sys.stderr)

    def tick(self, day: int, period: str, tick: int) -> None:
        """Log a simulation tick."""
        self.tick_count += 1
        if self.tick_count % 10 == 0:  # Only log every 10th tick
            self.log(LogLevel.TICK, f"Day {day} {period} (tick {tick})")

    def decision(self, agent_id: str, action: str, reasoning: str = None) -> None:
        """Log an agent decision."""
        msg = f"Action: {action}"
        if reasoning:
            # Truncate reasoning to 60 chars
            short_reason = reasoning[:60] + "..." if len(reasoning) > 60 else reasoning
            msg += f" | {short_reason}"
        self.log(LogLevel.DECISION, msg, agent_id)

    def llm_call(self, agent_id: str, purpose: str) -> None:
        """Log an LLM call."""
        self.log(LogLevel.LLM, f"Calling LLM: {purpose}", agent_id)

    def llm_response(self, agent_id: str, tokens: int = None) -> None:
        """Log LLM response received."""
        msg = "LLM response received"
        if tokens:
            msg += f" ({tokens} tokens)"
        self.log(LogLevel.LLM, msg, agent_id)

    def memory_add(self, agent_id: str, memory_type: str, content: str) -> None:
        """Log a memory being added."""
        short_content = content[:50] + "..." if len(content) > 50 else content
        self.log(LogLevel.MEMORY, f"New {memory_type}: {short_content}", agent_id)

    def reflection(self, agent_id: str, belief: str) -> None:
        """Log a reflection/belief formed."""
        short_belief = belief[:60] + "..." if len(belief) > 60 else belief
        self.log(LogLevel.REFLECTION, f"New belief: {short_belief}", agent_id)

    def culture_update(self, culture_id: str, change: str) -> None:
        """Log a culture update."""
        self.log(LogLevel.CULTURE, f"[{culture_id}] {change}")

    def file_write(self, path: str) -> None:
        """Log a file being written."""
        self.log(LogLevel.FILE, f"Updated: {path}")

    def error(self, message: str, agent_id: str = None) -> None:
        """Log an error."""
        self.log(LogLevel.ERROR, message, agent_id)


# Global logger instance
logger = SimulationLogger(verbose=True)