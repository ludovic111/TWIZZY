"""Error handling and recovery for TWIZZY.

Provides structured error handling, retry logic, and graceful degradation.
"""
import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    WARNING = "warning"  # Non-critical, can continue
    ERROR = "error"      # Failed operation, but agent can continue
    CRITICAL = "critical"  # Agent needs to restart or stop
    FATAL = "fatal"      # Unrecoverable error


@dataclass
class ErrorContext:
    """Context for an error."""

    operation: str
    severity: ErrorSeverity
    message: str
    exception: Exception | None = None
    retry_count: int = 0
    metadata: dict[str, Any] | None = None


class RetryStrategy:
    """Configurable retry strategy."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Exception types that should trigger retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±25%)
            delay *= (0.75 + random.random() * 0.5)

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an operation should be retried.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number

        Returns:
            True if should retry
        """
        if attempt >= self.max_retries:
            return False

        return isinstance(exception, self.retryable_exceptions)


# Default retry strategies
DEFAULT_RETRY = RetryStrategy(max_retries=3, base_delay=1.0)
LLM_RETRY = RetryStrategy(
    max_retries=3,
    base_delay=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError, asyncio.TimeoutError),
)
FILE_RETRY = RetryStrategy(
    max_retries=2,
    base_delay=0.5,
    retryable_exceptions=(PermissionError, OSError),
)


def with_retry(
    strategy: RetryStrategy | None = None,
    on_retry: Callable[[ErrorContext], None] | None = None,
    on_failure: Callable[[ErrorContext], None] | None = None,
):
    """Decorator for adding retry logic to async functions.

    Args:
        strategy: Retry strategy to use
        on_retry: Callback for retry events
        on_failure: Callback for final failure

    Returns:
        Decorated function
    """
    if strategy is None:
        strategy = DEFAULT_RETRY

    def decorator(func: Callable[..., asyncio.Future[T]]) -> Callable[..., asyncio.Future[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(strategy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if not strategy.should_retry(e, attempt):
                        break

                    delay = strategy.calculate_delay(attempt)

                    context = ErrorContext(
                        operation=func.__name__,
                        severity=ErrorSeverity.WARNING,
                        message=f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        exception=e,
                        retry_count=attempt,
                    )

                    logger.warning(f"{context.message}: {str(e)}")

                    if on_retry:
                        on_retry(context)

                    await asyncio.sleep(delay)

            # All retries exhausted
            final_context = ErrorContext(
                operation=func.__name__,
                severity=ErrorSeverity.ERROR,
                message=f"All {strategy.max_retries + 1} attempts failed",
                exception=last_exception,
                retry_count=strategy.max_retries,
            )

            logger.error(final_context.message)

            if on_failure:
                on_failure(final_context)

            raise last_exception or RuntimeError("Operation failed after retries")

        return wrapper
    return decorator


class ErrorBoundary:
    """Error boundary for isolating failures."""

    def __init__(
        self,
        name: str,
        on_error: Callable[[ErrorContext], None] | None = None,
        fallback_value: Any = None,
        suppress_errors: bool = False,
    ):
        """Initialize error boundary.

        Args:
            name: Name of the boundary
            on_error: Error handler callback
            fallback_value: Value to return on error
            suppress_errors: Whether to suppress errors
        """
        self.name = name
        self.on_error = on_error
        self.fallback_value = fallback_value
        self.suppress_errors = suppress_errors
        self._error_count = 0
        self._last_error: ErrorContext | None = None

    async def run(self, func: Callable[..., asyncio.Future[T]], *args, **kwargs) -> T | Any:
        """Run a function within the error boundary.

        Args:
            func: Function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result or fallback value
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            self._error_count += 1

            context = ErrorContext(
                operation=self.name,
                severity=ErrorSeverity.ERROR,
                message=f"Error in {self.name}: {str(e)}",
                exception=e,
            )

            self._last_error = context
            logger.error(context.message, exc_info=True)

            if self.on_error:
                self.on_error(context)

            if self.suppress_errors:
                return self.fallback_value

            raise

    def get_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        return {
            "name": self.name,
            "error_count": self._error_count,
            "last_error": self._last_error.message if self._last_error else None,
            "last_error_time": self._last_error.timestamp if self._last_error else None,
        }


class CircuitBreaker:
    """Circuit breaker pattern for failing operations."""

    class State(Enum):
        """Circuit breaker states."""

        CLOSED = "closed"      # Normal operation
        OPEN = "open"          # Failing, reject requests
        HALF_OPEN = "half_open"  # Testing if recovered

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker.

        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds before attempting recovery
            half_open_max_calls: Max calls in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> State:
        """Get current state."""
        # Check if we should transition from OPEN to HALF_OPEN
        if self._state == self.State.OPEN:
            if self._last_failure_time and (time.time() - self._last_failure_time) > self.recovery_timeout:
                self._state = self.State.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")

        return self._state

    def record_success(self) -> None:
        """Record a successful operation."""
        if self._state == self.State.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = self.State.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed (recovered)")
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == self.State.HALF_OPEN:
            self._state = self.State.OPEN
            logger.warning(f"Circuit breaker '{self.name}' reopened due to failure")
        elif self._failure_count >= self.failure_threshold:
            self._state = self.State.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened after {self._failure_count} failures")

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        state = self.state  # This may trigger state transition

        if state == self.State.CLOSED:
            return True
        elif state == self.State.OPEN:
            return False
        elif state == self.State.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    async def call(self, func: Callable[..., asyncio.Future[T]], *args, **kwargs) -> T:
        """Call a function through the circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RuntimeError: If circuit is open
        """
        if not self.can_execute():
            raise RuntimeError(f"Circuit breaker '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
        }


# Global error handler
_error_handler: logging.Handler | None = None


def setup_error_handling() -> None:
    """Set up global error handling."""
    global _error_handler

    # Create error handler that logs to separate file
    from pathlib import Path

    error_log = Path.home() / ".twizzy" / "logs" / "errors.log"
    error_log.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(error_log)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    # Add to root logger
    logging.getLogger().addHandler(handler)
    _error_handler = handler

    logger.info("Error handling configured")
