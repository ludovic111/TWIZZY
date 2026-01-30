"""Rate limiting for API calls and resource usage.

Prevents hitting API limits and manages resource consumption.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 50  # Max requests per window
    window_seconds: float = 60.0  # Time window
    max_concurrent: int = 5  # Max concurrent requests
    min_delay_between_requests: float = 0.1  # Minimum delay between requests


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""
    total_requests: int = 0
    throttled_requests: int = 0
    current_window_requests: int = 0
    average_wait_time_ms: float = 0.0
    last_request_time: float = field(default_factory=time.time)


class RateLimiter:
    """Token bucket rate limiter for API calls.
    
    Ensures we don't exceed rate limits while maximizing throughput.
    """
    
    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()
        self._request_times: deque[float] = deque()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._lock = asyncio.Lock()
        self.stats = RateLimitStats()
    
    async def acquire(self) -> bool:
        """Acquire permission to make a request.
        
        Returns:
            True if acquired, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            cutoff = now - self.config.window_seconds
            while self._request_times and self._request_times[0] < cutoff:
                self._request_times.popleft()
            
            # Check if we're at the limit
            if len(self._request_times) >= self.config.max_requests:
                self.stats.throttled_requests += 1
                logger.warning(f"Rate limit hit: {len(self._request_times)} requests in window")
                return False
            
            # Enforce minimum delay between requests
            time_since_last = now - self.stats.last_request_time
            if time_since_last < self.config.min_delay_between_requests:
                delay = self.config.min_delay_between_requests - time_since_last
                await asyncio.sleep(delay)
                now = time.time()
            
            # Record this request
            self._request_times.append(now)
            self.stats.total_requests += 1
            self.stats.current_window_requests = len(self._request_times)
            self.stats.last_request_time = now
            
            return True
    
    async def __aenter__(self):
        """Context manager entry - acquire semaphore."""
        await self._semaphore.acquire()
        acquired = await self.acquire()
        if not acquired:
            self._semaphore.release()
            raise RateLimitExceeded("Rate limit exceeded")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - release semaphore."""
        self._semaphore.release()
    
    def get_stats(self) -> dict:
        """Get current rate limiting statistics."""
        return {
            "total_requests": self.stats.total_requests,
            "throttled_requests": self.stats.throttled_requests,
            "current_window_requests": len(self._request_times),
            "max_requests": self.config.max_requests,
            "window_seconds": self.config.window_seconds,
        }
    
    def reset(self):
        """Reset rate limiter state."""
        self._request_times.clear()
        self.stats = RateLimitStats()


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on API responses.
    
    Slows down if receiving 429 (Too Many Requests) errors,
    speeds up if consistently successful.
    """
    
    def __init__(self, config: RateLimitConfig | None = None):
        super().__init__(config)
        self._success_count = 0
        self._failure_count = 0
        self._adaptive_delay = 0.0
    
    def report_success(self):
        """Report a successful request."""
        self._success_count += 1
        self._failure_count = max(0, self._failure_count - 1)
        
        # Gradually reduce adaptive delay on success
        if self._success_count >= 10:
            self._adaptive_delay = max(0, self._adaptive_delay * 0.9)
            self._success_count = 0
    
    def report_rate_limit_hit(self, retry_after: float | None = None):
        """Report that we hit a rate limit."""
        self._failure_count += 1
        self._success_count = 0
        
        # Increase adaptive delay
        if retry_after:
            self._adaptive_delay = retry_after
        else:
            self._adaptive_delay = min(5.0, self._adaptive_delay + 0.5)
        
        logger.warning(f"Adaptive delay increased to {self._adaptive_delay}s")
    
    async def acquire(self) -> bool:
        """Acquire with adaptive delay."""
        if self._adaptive_delay > 0:
            await asyncio.sleep(self._adaptive_delay)
        
        return await super().acquire()


def with_rate_limit(limiter: RateLimiter):
    """Decorator to apply rate limiting to a function.
    
    Usage:
        limiter = RateLimiter()
        
        @with_rate_limit(limiter)
        async def api_call():
            return await make_request()
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            async with limiter:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
