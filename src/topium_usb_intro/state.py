"""Device session deduplication and connection transitions (pure Python)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SessionTracker:
    # Present profiles are not re-triggered on duplicate arrival notifications.
    present: set[str] = field(default_factory=set)
    missing_counts: dict[str, int] = field(default_factory=dict)
    initialized: bool = False

    def observe(self, matched_ids: set[str], *, allow_initial: bool = False,
                confirmed_removal: bool = False) -> list[str]:
        if not self.initialized:
            self.initialized = True
            self.present = matched_ids.copy()
            return sorted(matched_ids) if allow_initial else []
        arrivals: list[str] = []
        for profile_id in matched_ids:
            self.missing_counts.pop(profile_id, None)
            if profile_id not in self.present:
                self.present.add(profile_id)
                arrivals.append(profile_id)
        for profile_id in self.present - matched_ids:
            count = self.missing_counts.get(profile_id, 0) + 1
            if confirmed_removal or count >= 2:
                self.present.discard(profile_id)
                self.missing_counts.pop(profile_id, None)
            else:
                self.missing_counts[profile_id] = count
        return sorted(arrivals)

    def rebaseline(self, matched_ids: set[str]) -> None:
        """Reconfigure profiles without playing intros for already present media."""
        self.initialized = True
        self.present = matched_ids.copy()
        self.missing_counts.clear()
