from __future__ import annotations

import math
import time
from collections import deque


class SlidingWindowLimiter:
    """A tiny in-process limiter for a single-instance demo deployment."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        now = time.monotonic()
        bucket = self._events.setdefault(key, deque())

        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(
                1,
                math.ceil(bucket[0] + window_seconds - now),
            )
            return False, retry_after

        bucket.append(now)
        return True, 0

    def reset(self) -> None:
        self._events.clear()
