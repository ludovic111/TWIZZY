"""Health monitoring for TWIZZY.

Provides health checks for all agent components.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from .llm.kimi_client import KimiClient
from ..plugins import PluginRegistry

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str
    last_check: datetime
    response_time_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health."""

    status: HealthStatus
    components: list[ComponentHealth]
    checked_at: datetime
    overall_message: str


class HealthChecker:
    """Health checker for TWIZZY components."""

    def __init__(self):
        """Initialize the health checker."""
        self.checks: dict[str, Callable[[], asyncio.Future[ComponentHealth]]] = {}
        self._last_results: dict[str, ComponentHealth] = {}

    def register_check(
        self,
        name: str,
        check_func: Callable[[], asyncio.Future[ComponentHealth]],
    ) -> None:
        """Register a health check.

        Args:
            name: Name of the component
            check_func: Async function that returns ComponentHealth
        """
        self.checks[name] = check_func
        logger.debug(f"Registered health check: {name}")

    def unregister_check(self, name: str) -> None:
        """Unregister a health check.

        Args:
            name: Name of the component
        """
        if name in self.checks:
            del self.checks[name]
            if name in self._last_results:
                del self._last_results[name]

    async def check_all(self) -> SystemHealth:
        """Run all health checks.

        Returns:
            SystemHealth with all component statuses
        """
        start_time = time.time()
        components = []

        # Run all checks concurrently
        tasks = [
            self._run_check(name, check_func)
            for name, check_func in self.checks.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                # Create unhealthy component for failed checks
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}",
                    last_check=datetime.now(),
                    response_time_ms=0,
                ))
            else:
                components.append(result)
                self._last_results[result.name] = result

        # Determine overall status
        statuses = [c.status for c in components]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
            overall_message = "One or more components are unhealthy"
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
            overall_message = "One or more components are degraded"
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
            overall_message = "All components are healthy"
        else:
            overall_status = HealthStatus.UNKNOWN
            overall_message = "Some components have unknown status"

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug(f"Health check completed in {elapsed_ms:.2f}ms: {overall_status.value}")

        return SystemHealth(
            status=overall_status,
            components=components,
            checked_at=datetime.now(),
            overall_message=overall_message,
        )

    async def _run_check(
        self,
        name: str,
        check_func: Callable[[], asyncio.Future[ComponentHealth]],
    ) -> ComponentHealth:
        """Run a single health check with timeout.

        Args:
            name: Component name
            check_func: Check function

        Returns:
            ComponentHealth result
        """
        start_time = time.time()

        try:
            # Run check with 10 second timeout
            result = await asyncio.wait_for(check_func(), timeout=10.0)
            result.response_time_ms = (time.time() - start_time) * 1000
            return result
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Health check timed out after 10 seconds",
                last_check=datetime.now(),
                response_time_ms=10000,
            )
        except Exception as e:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    def get_last_result(self, name: str) -> ComponentHealth | None:
        """Get the last health check result for a component.

        Args:
            name: Component name

        Returns:
            Last ComponentHealth or None
        """
        return self._last_results.get(name)


class AgentHealthMonitor:
    """Health monitor for the TWIZZY agent."""

    def __init__(self, kimi_client: KimiClient | None = None, registry: PluginRegistry | None = None):
        """Initialize the health monitor.

        Args:
            kimi_client: The Kimi client to monitor
            registry: The plugin registry to monitor
        """
        self.checker = HealthChecker()
        self.kimi_client = kimi_client
        self.registry = registry

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.checker.register_check("llm_connection", self._check_llm_connection)
        self.checker.register_check("plugins", self._check_plugins)
        self.checker.register_check("system", self._check_system)

    async def _check_llm_connection(self) -> ComponentHealth:
        """Check LLM connection health."""
        if self.kimi_client is None:
            return ComponentHealth(
                name="llm_connection",
                status=HealthStatus.UNHEALTHY,
                message="Kimi client not initialized",
                last_check=datetime.now(),
                response_time_ms=0,
            )

        try:
            # Try a simple request
            from .llm.kimi_client import Message

            start = time.time()
            response = await self.kimi_client.chat(
                [Message(role="user", content="Hi")],
                thinking=False,
            )
            elapsed_ms = (time.time() - start) * 1000

            if response.content is not None:
                return ComponentHealth(
                    name="llm_connection",
                    status=HealthStatus.HEALTHY,
                    message="Kimi API is responding",
                    last_check=datetime.now(),
                    response_time_ms=elapsed_ms,
                    metadata={"model": self.kimi_client.config.model},
                )
            else:
                return ComponentHealth(
                    name="llm_connection",
                    status=HealthStatus.DEGRADED,
                    message="Kimi API returned empty response",
                    last_check=datetime.now(),
                    response_time_ms=elapsed_ms,
                )

        except Exception as e:
            return ComponentHealth(
                name="llm_connection",
                status=HealthStatus.UNHEALTHY,
                message=f"Kimi API error: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=0,
            )

    async def _check_plugins(self) -> ComponentHealth:
        """Check plugin health."""
        if self.registry is None:
            return ComponentHealth(
                name="plugins",
                status=HealthStatus.UNHEALTHY,
                message="Plugin registry not initialized",
                last_check=datetime.now(),
                response_time_ms=0,
            )

        plugins = self.registry.get_all_plugins()
        plugin_names = [p.name for p in plugins]

        return ComponentHealth(
            name="plugins",
            status=HealthStatus.HEALTHY,
            message=f"{len(plugins)} plugins registered",
            last_check=datetime.now(),
            response_time_ms=0,
            metadata={"registered_plugins": plugin_names},
        )

    async def _check_system(self) -> ComponentHealth:
        """Check system resources."""
        import psutil

        try:
            # Check memory
            memory = psutil.virtual_memory()
            memory_status = HealthStatus.HEALTHY
            memory_message = f"Memory: {memory.percent}% used"

            if memory.percent > 90:
                memory_status = HealthStatus.UNHEALTHY
                memory_message = f"Critical memory usage: {memory.percent}%"
            elif memory.percent > 75:
                memory_status = HealthStatus.DEGRADED
                memory_message = f"High memory usage: {memory.percent}%"

            # Check disk
            disk = psutil.disk_usage("/")
            disk_status = HealthStatus.HEALTHY
            disk_message = f"Disk: {disk.percent}% used"

            if disk.percent > 90:
                disk_status = HealthStatus.UNHEALTHY
                disk_message = f"Critical disk usage: {disk.percent}%"
            elif disk.percent > 80:
                disk_status = HealthStatus.DEGRADED
                disk_message = f"High disk usage: {disk.percent}%"

            # Overall status
            if memory_status == HealthStatus.UNHEALTHY or disk_status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                overall_message = f"{memory_message}, {disk_message}"
            elif memory_status == HealthStatus.DEGRADED or disk_status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED
                overall_message = f"{memory_message}, {disk_message}"
            else:
                overall_status = HealthStatus.HEALTHY
                overall_message = f"{memory_message}, {disk_message}"

            return ComponentHealth(
                name="system",
                status=overall_status,
                message=overall_message,
                last_check=datetime.now(),
                response_time_ms=0,
                metadata={
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                },
            )

        except Exception as e:
            return ComponentHealth(
                name="system",
                status=HealthStatus.UNKNOWN,
                message=f"Could not check system resources: {str(e)}",
                last_check=datetime.now(),
                response_time_ms=0,
            )

    async def check_health(self) -> SystemHealth:
        """Run all health checks.

        Returns:
            SystemHealth with all component statuses
        """
        return await self.checker.check_all()


# Global monitor instance
_monitor: AgentHealthMonitor | None = None


def get_health_monitor(kimi_client: KimiClient | None = None, registry: PluginRegistry | None = None) -> AgentHealthMonitor:
    """Get the global health monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = AgentHealthMonitor(kimi_client, registry)
    return _monitor
