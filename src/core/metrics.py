"""Metrics collection for TWIZZY.

Tracks performance, usage, and health metrics over time.
"""
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolMetrics:
    """Metrics for a specific tool."""
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    last_called: float | None = None
    
    def record_call(self, duration_ms: float, success: bool):
        """Record a tool execution."""
        self.call_count += 1
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.call_count
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.last_called = time.time()
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / max(self.call_count, 1),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "max_duration_ms": round(self.max_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2) if self.min_duration_ms != float('inf') else 0,
            "last_called": datetime.fromtimestamp(self.last_called).isoformat() if self.last_called else None,
        }


@dataclass
class SessionMetrics:
    """Metrics for the current session."""
    session_start: float = field(default_factory=time.time)
    messages_processed: int = 0
    tools_executed: int = 0
    llm_calls: int = 0
    llm_errors: int = 0
    total_llm_tokens: int = 0
    errors: int = 0
    
    # Timing
    total_processing_time_ms: float = 0.0
    avg_message_time_ms: float = 0.0
    
    def record_message(self, processing_time_ms: float):
        """Record a processed message."""
        self.messages_processed += 1
        self.total_processing_time_ms += processing_time_ms
        self.avg_message_time_ms = self.total_processing_time_ms / self.messages_processed
    
    def record_llm_call(self, tokens_used: int = 0, error: bool = False):
        """Record an LLM API call."""
        self.llm_calls += 1
        self.total_llm_tokens += tokens_used
        if error:
            self.llm_errors += 1
    
    def to_dict(self) -> dict[str, Any]:
        uptime = time.time() - self.session_start
        return {
            "session_start": datetime.fromtimestamp(self.session_start).isoformat(),
            "uptime_seconds": round(uptime, 2),
            "messages_processed": self.messages_processed,
            "tools_executed": self.tools_executed,
            "llm_calls": self.llm_calls,
            "llm_errors": self.llm_errors,
            "llm_error_rate": self.llm_errors / max(self.llm_calls, 1),
            "total_llm_tokens": self.total_llm_tokens,
            "errors": self.errors,
            "avg_message_time_ms": round(self.avg_message_time_ms, 2),
        }


class MetricsCollector:
    """Collects and stores metrics for TWIZZY.
    
    Tracks:
    - Tool usage and performance
    - LLM API usage
    - Error rates
    - Session statistics
    """
    
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or Path.home() / ".twizzy" / "metrics"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = SessionMetrics()
        self.tool_metrics: dict[str, ToolMetrics] = {}
        
        # Historical data (keep last 1000 points)
        self._message_times: deque[float] = deque(maxlen=1000)
        self._error_log: deque[dict] = deque(maxlen=100)
        
        # Load historical data
        self._load_metrics()
    
    def _load_metrics(self):
        """Load historical metrics from disk."""
        metrics_file = self.storage_dir / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                
                # Restore tool metrics
                for tool_name, tool_data in data.get("tools", {}).items():
                    self.tool_metrics[tool_name] = ToolMetrics(
                        tool_name=tool_name,
                        call_count=tool_data.get("call_count", 0),
                        success_count=tool_data.get("success_count", 0),
                        error_count=tool_data.get("error_count", 0),
                    )
                    
            except Exception as e:
                logger.warning(f"Failed to load metrics: {e}")
    
    def save_metrics(self):
        """Save metrics to disk."""
        try:
            metrics_file = self.storage_dir / "metrics.json"
            data = {
                "saved_at": datetime.now().isoformat(),
                "session": self.session.to_dict(),
                "tools": {
                    name: metrics.to_dict()
                    for name, metrics in self.tool_metrics.items()
                },
            }
            
            with open(metrics_file, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error_message: str | None = None,
    ):
        """Record a tool execution.
        
        Args:
            tool_name: Name of the tool
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            error_message: Error message if failed
        """
        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = ToolMetrics(tool_name=tool_name)
        
        self.tool_metrics[tool_name].record_call(duration_ms, success)
        self.session.tools_executed += 1
        
        if not success and error_message:
            self._error_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "tool_error",
                "tool": tool_name,
                "error": error_message,
            })
            self.session.errors += 1
    
    def record_message_processed(self, processing_time_ms: float):
        """Record a successfully processed message."""
        self.session.record_message(processing_time_ms)
        self._message_times.append(processing_time_ms)
    
    def record_llm_call(self, tokens_used: int = 0, error: bool = False):
        """Record an LLM API call."""
        self.session.record_llm_call(tokens_used, error)
        
        if error:
            self._error_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "llm_error",
            })
            self.session.errors += 1
    
    def get_tool_summary(self) -> dict[str, dict]:
        """Get summary of all tool metrics."""
        return {
            name: metrics.to_dict()
            for name, metrics in self.tool_metrics.items()
        }
    
    def get_top_tools(self, n: int = 5) -> list[ToolMetrics]:
        """Get top N most used tools."""
        sorted_tools = sorted(
            self.tool_metrics.values(),
            key=lambda t: t.call_count,
            reverse=True
        )
        return sorted_tools[:n]
    
    def get_slowest_tools(self, n: int = 5) -> list[ToolMetrics]:
        """Get top N slowest tools by average duration."""
        sorted_tools = sorted(
            self.tool_metrics.values(),
            key=lambda t: t.avg_duration_ms,
            reverse=True
        )
        return sorted_tools[:n]
    
    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of recent errors."""
        tool_errors = sum(1 for e in self._error_log if e["type"] == "tool_error")
        llm_errors = sum(1 for e in self._error_log if e["type"] == "llm_error")
        
        return {
            "total_errors": len(self._error_log),
            "tool_errors": tool_errors,
            "llm_errors": llm_errors,
            "recent_errors": list(self._error_log)[-10:],
        }
    
    def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        if not self._message_times:
            return {
                "avg_processing_time_ms": 0,
                "min_processing_time_ms": 0,
                "max_processing_time_ms": 0,
                "p95_processing_time_ms": 0,
            }
        
        times = list(self._message_times)
        times.sort()
        
        p95_index = int(len(times) * 0.95)
        
        return {
            "avg_processing_time_ms": round(sum(times) / len(times), 2),
            "min_processing_time_ms": round(min(times), 2),
            "max_processing_time_ms": round(max(times), 2),
            "p95_processing_time_ms": round(times[min(p95_index, len(times) - 1)], 2),
        }
    
    def get_full_report(self) -> dict[str, Any]:
        """Get complete metrics report."""
        return {
            "session": self.session.to_dict(),
            "tools": self.get_tool_summary(),
            "top_tools": [t.to_dict() for t in self.get_top_tools()],
            "slowest_tools": [t.to_dict() for t in self.get_slowest_tools()],
            "errors": self.get_error_summary(),
            "performance": self.get_performance_stats(),
        }


def track_tool_execution(collector: MetricsCollector):
    """Decorator to track tool execution metrics.
    
    Usage:
        @track_tool_execution(metrics_collector)
        async def my_tool():
            return await do_something()
    """
    def decorator(func: Callable):
        tool_name = func.__name__
        
        async def wrapper(*args, **kwargs):
            start = time.time()
            success = True
            error_msg = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                collector.record_tool_call(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_msg,
                )
        
        return wrapper
    return decorator


# Global metrics instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
