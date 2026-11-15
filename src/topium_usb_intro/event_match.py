"""Pure event-device identity rules and short duplicate-notification throttle."""
from __future__ import annotations
from .models import Profile


def normalized_id(value: str) -> str:
    return value.strip().rstrip("\\").casefold()


def event_matches_profile(event_device_id: str, profile: Profile) -> bool:
    return bool(event_device_id and profile.disk_pnp_id and
                normalized_id(event_device_id) == normalized_id(profile.disk_pnp_id))


def should_play(now: float, previous: float, *, cooldown: float = 5) -> bool:
    return now >= previous + cooldown
