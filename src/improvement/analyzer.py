"""Improvement analyzer - Detects optimization opportunities.

This module analyzes agent activity to find opportunities for self-improvement:
- Failed tasks that could be improved
- Slow operations that could be optimized
- Repetitive patterns that could be automated
- User requests that require new capabilities
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ImprovementType(Enum):
    """Types of improvements that can be detected."""

    FIX_FAILURE = "fix_failure"  # A task that failed
    OPTIMIZE_SPEED = "optimize_speed"  # A slow operation
    NEW_CAPABILITY = "new_capability"  # A requested feature
    CODE_QUALITY = "code_quality"  # Code improvements
    PATTERN_AUTOMATION = "pattern_automation"  # Repetitive patterns


@dataclass
class TaskRecord:
    """Record of a task execution."""

    task_id: str
    user_request: str
    tools_used: list[str]
    success: bool
    error_message: str | None
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "tools_used": self.tools_used,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ImprovementOpportunity:
    """An opportunity for improvement detected by the analyzer."""

    id: str
    type: ImprovementType
    description: str
    priority: int  # 1-10, higher = more important
    context: dict[str, Any]
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "priority": self.priority,
            "context": self.context,
            "detected_at": self.detected_at.isoformat(),
        }


class ImprovementAnalyzer:
    """Analyzes agent activity to find improvement opportunities."""

    def __init__(self, history_file: Path | None = None):
        """Initialize the analyzer.

        Args:
            history_file: Path to store task history
        """
        self.history_file = history_file or Path.home() / ".twizzy" / "task_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.task_history: list[TaskRecord] = []
        self.opportunities: list[ImprovementOpportunity] = []
        self._load_history()

    def _load_history(self):
        """Load task history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    data = json.load(f)
                    self.task_history = [
                        TaskRecord(
                            task_id=t["task_id"],
                            user_request=t["user_request"],
                            tools_used=t["tools_used"],
                            success=t["success"],
                            error_message=t.get("error_message"),
                            duration_ms=t["duration_ms"],
                            timestamp=datetime.fromisoformat(t["timestamp"]),
                        )
                        for t in data.get("tasks", [])
                    ]
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")

    def _save_history(self):
        """Save task history to file."""
        try:
            with open(self.history_file, "w") as f:
                json.dump({
                    "tasks": [t.to_dict() for t in self.task_history[-1000:]],  # Keep last 1000
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def record_task(self, task: TaskRecord):
        """Record a task execution for analysis.

        Args:
            task: The task record to add
        """
        self.task_history.append(task)
        self._save_history()
        logger.debug(f"Recorded task: {task.task_id} (success={task.success})")

    def analyze(self) -> list[ImprovementOpportunity]:
        """Analyze task history and find improvement opportunities.

        Returns:
            List of detected improvement opportunities
        """
        self.opportunities.clear()

        # Analyze different aspects
        self._analyze_failures()
        self._analyze_slow_operations()
        self._analyze_patterns()
        self._analyze_missing_capabilities()

        # Sort by priority
        self.opportunities.sort(key=lambda x: x.priority, reverse=True)

        logger.info(f"Found {len(self.opportunities)} improvement opportunities")
        return self.opportunities

    def _analyze_failures(self):
        """Find recurring failures that could be fixed."""
        # Group recent failures by error type
        recent = [
            t for t in self.task_history
            if not t.success and t.timestamp > datetime.now() - timedelta(days=7)
        ]

        error_groups: dict[str, list[TaskRecord]] = {}
        for task in recent:
            error_key = task.error_message or "unknown"
            if error_key not in error_groups:
                error_groups[error_key] = []
            error_groups[error_key].append(task)

        # Create opportunities for recurring failures
        for error, tasks in error_groups.items():
            if len(tasks) >= 2:  # At least 2 similar failures
                opp = ImprovementOpportunity(
                    id=f"fix-{hash(error) % 10000:04d}",
                    type=ImprovementType.FIX_FAILURE,
                    description=f"Fix recurring failure: {error[:100]}",
                    priority=min(len(tasks) + 5, 10),  # More failures = higher priority
                    context={
                        "error_message": error,
                        "occurrence_count": len(tasks),
                        "sample_requests": [t.user_request for t in tasks[:3]],
                        "tools_involved": list(set(tool for t in tasks for tool in t.tools_used)),
                    }
                )
                self.opportunities.append(opp)

    def _analyze_slow_operations(self):
        """Find operations that could be optimized for speed."""
        # Find tasks that took longer than average
        if len(self.task_history) < 10:
            return

        successful = [t for t in self.task_history if t.success]
        if not successful:
            return

        avg_duration = sum(t.duration_ms for t in successful) / len(successful)
        slow_threshold = avg_duration * 3  # 3x slower than average

        slow_tasks = [
            t for t in successful
            if t.duration_ms > slow_threshold and t.timestamp > datetime.now() - timedelta(days=7)
        ]

        # Group by tools used
        tool_durations: dict[str, list[int]] = {}
        for task in slow_tasks:
            for tool in task.tools_used:
                if tool not in tool_durations:
                    tool_durations[tool] = []
                tool_durations[tool].append(task.duration_ms)

        for tool, durations in tool_durations.items():
            if len(durations) >= 2:
                avg_tool_duration = sum(durations) / len(durations)
                opp = ImprovementOpportunity(
                    id=f"optimize-{tool[:20]}",
                    type=ImprovementType.OPTIMIZE_SPEED,
                    description=f"Optimize slow tool: {tool}",
                    priority=6,
                    context={
                        "tool_name": tool,
                        "avg_duration_ms": int(avg_tool_duration),
                        "occurrence_count": len(durations),
                    }
                )
                self.opportunities.append(opp)

    def _analyze_patterns(self):
        """Find repetitive patterns that could be automated."""
        # Look for similar request sequences
        recent = [
            t for t in self.task_history
            if t.timestamp > datetime.now() - timedelta(days=7)
        ]

        # Simple pattern detection: same tool sequence used multiple times
        tool_sequences: dict[str, int] = {}
        for task in recent:
            seq_key = ",".join(task.tools_used)
            if len(task.tools_used) >= 2:  # Only multi-step patterns
                tool_sequences[seq_key] = tool_sequences.get(seq_key, 0) + 1

        for seq, count in tool_sequences.items():
            if count >= 3:  # Pattern repeated at least 3 times
                tools = seq.split(",")
                opp = ImprovementOpportunity(
                    id=f"automate-{hash(seq) % 10000:04d}",
                    type=ImprovementType.PATTERN_AUTOMATION,
                    description=f"Create automation for common pattern: {' -> '.join(tools[:3])}",
                    priority=5,
                    context={
                        "tool_sequence": tools,
                        "occurrence_count": count,
                    }
                )
                self.opportunities.append(opp)

    def _analyze_missing_capabilities(self):
        """Find requests that couldn't be fulfilled due to missing capabilities."""
        recent_failures = [
            t for t in self.task_history
            if not t.success
            and t.timestamp > datetime.now() - timedelta(days=7)
            and t.error_message
            and ("not found" in t.error_message.lower() or "not supported" in t.error_message.lower())
        ]

        # Group by similar requests
        capability_requests: dict[str, list[str]] = {}
        for task in recent_failures:
            # Extract key words from request
            key = task.user_request.lower()[:50]
            if key not in capability_requests:
                capability_requests[key] = []
            capability_requests[key].append(task.user_request)

        for key, requests in capability_requests.items():
            if len(requests) >= 2:
                opp = ImprovementOpportunity(
                    id=f"capability-{hash(key) % 10000:04d}",
                    type=ImprovementType.NEW_CAPABILITY,
                    description=f"Add new capability for: {requests[0][:50]}...",
                    priority=7,
                    context={
                        "sample_requests": requests[:3],
                        "request_count": len(requests),
                    }
                )
                self.opportunities.append(opp)

    def get_top_opportunities(self, n: int = 5) -> list[ImprovementOpportunity]:
        """Get the top N improvement opportunities.

        Args:
            n: Number of opportunities to return

        Returns:
            List of top opportunities sorted by priority
        """
        if not self.opportunities:
            self.analyze()
        return self.opportunities[:n]
