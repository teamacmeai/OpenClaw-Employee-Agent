import threading
import time


class TokenBucketRateLimiter:
    """In-memory thread-safe token bucket rate limiter per key (e.g. workstation_id)."""

    def __init__(self, rate_per_minute: int = 60, burst_capacity: int | None = None) -> None:
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = float(burst_capacity if burst_capacity is not None else rate_per_minute)
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refreshed_at)
        self._lock = threading.Lock()

    def check(self, key: str, tokens_requested: float = 1.0) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Returns (allowed, retry_after_seconds).
        If allowed is True, retry_after_seconds is 0.
        If allowed is False, retry_after_seconds indicates how many seconds to wait.
        """
        now = time.time()
        with self._lock:
            tokens, last_time = self._buckets.get(key, (self.capacity, now))
            # Replenish tokens based on elapsed time
            elapsed = now - last_time
            tokens = min(self.capacity, tokens + elapsed * self.rate_per_second)

            if tokens >= tokens_requested:
                tokens -= tokens_requested
                self._buckets[key] = (tokens, now)
                return True, 0
            else:
                self._buckets[key] = (tokens, now)
                needed = tokens_requested - tokens
                wait_seconds = int(needed / self.rate_per_second) + 1
                return False, wait_seconds

    def reset(self) -> None:
        """Clear all buckets (useful for tests)."""
        with self._lock:
            self._buckets.clear()
