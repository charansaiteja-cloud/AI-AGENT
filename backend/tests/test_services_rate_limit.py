from __future__ import annotations

from backend.app.services.rate_limit import SlidingWindowLimiter


def test_allows_requests_below_the_limit() -> None:
    limiter = SlidingWindowLimiter()

    for _ in range(3):
        allowed, retry_after = limiter.check("chat:1.2.3.4", limit=3)

        assert allowed is True
        assert retry_after == 0


def test_blocks_requests_at_the_limit() -> None:
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        limiter.check("chat:1.2.3.4", limit=3)

    allowed, retry_after = limiter.check("chat:1.2.3.4", limit=3)

    assert allowed is False
    assert retry_after >= 1


def test_keys_are_isolated() -> None:
    limiter = SlidingWindowLimiter()
    limiter.check("chat:one", limit=1)

    allowed, _ = limiter.check("chat:two", limit=1)

    assert allowed is True


def test_window_expiry_releases_slots(monkeypatch) -> None:
    now = 1000.0
    monkeypatch.setattr("backend.app.services.rate_limit.time.monotonic", lambda: now)
    limiter = SlidingWindowLimiter()
    limiter.check("chat:one", limit=1, window_seconds=60)

    assert limiter.check("chat:one", limit=1, window_seconds=60)[0] is False

    now += 61
    assert limiter.check("chat:one", limit=1, window_seconds=60)[0] is True


def test_reset_clears_every_bucket() -> None:
    limiter = SlidingWindowLimiter()
    limiter.check("chat:one", limit=1)

    limiter.reset()

    assert limiter.check("chat:one", limit=1)[0] is True
