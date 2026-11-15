"""Pure data and matching logic; no Qt or Windows imports."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4


@dataclass(frozen=True)
class UsbVolume:
    disk_pnp_id: str
    disk_serial: str
    disk_model: str
    volume_serial: str
    volume_guid: str
    mount_point: str
    disk_index: int = -1
    bus_type: str = "USB"
    label: str = ""

    @property
    def friendly_name(self) -> str:
        return f"{self.mount_point}  •  {self.label or self.disk_model or 'USB disk'}"

    @property
    def mount(self) -> Path:
        return Path(self.mount_point)


@dataclass
class Profile:
    name: str
    disk_pnp_id: str
    volume_serial: str
    volume_guid: str
    disk_model: str = ""
    gif_path: str = ""
    folder_mode: Literal["root", "first", "multiple"] = "root"
    folders: list[str] = field(default_factory=list)
    open_explorer: bool = True
    enabled: bool = True
    size: int = 240
    position: Literal["center", "bottom-right"] = "bottom-right"
    fade_ms: int = 150
    max_duration_ms: int = 8000
    id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def from_volume(cls, volume: UsbVolume, *, name: str | None = None) -> "Profile":
        if not volume.disk_pnp_id.strip():
            raise ValueError("No physical PnP identifier is available. Refusing unsafe registration.")
        if not (volume.volume_serial.strip() or volume.volume_guid.strip()):
            raise ValueError("No volume identifier is available. Refusing unsafe registration.")
        if volume.bus_type != "USB":
            raise ValueError("The selected volume is not confirmed as attached by USB.")
        return cls(
            name=name or (volume.label or volume.disk_model or "My USB drive"),
            disk_pnp_id=volume.disk_pnp_id,
            volume_serial=volume.volume_serial,
            volume_guid=volume.volume_guid,
            disk_model=volume.disk_model,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Profile":
        if not isinstance(raw, dict):
            raise ValueError("Invalid profile data")
        allowed = cls.__dataclass_fields__.keys()
        values = {k: v for k, v in raw.items() if k in allowed}
        profile = cls(**values)
        if profile.folder_mode not in ("root", "first", "multiple"):
            raise ValueError("Invalid folder selection mode")
        if profile.position not in ("center", "bottom-right"):
            raise ValueError("Invalid overlay position")
        if not isinstance(profile.folders, list) or not all(isinstance(v, str) for v in profile.folders):
            raise ValueError("Invalid folder list")
        profile.size = max(64, min(800, int(profile.size)))
        profile.fade_ms = max(0, min(1500, int(profile.fade_ms)))
        profile.max_duration_ms = max(500, min(15000, int(profile.max_duration_ms)))
        return profile


def same_device(profile: Profile, candidate: UsbVolume) -> bool:
    """Fail closed; never select by drive letter, label or model alone.

    The physical PnP ID plus filesystem serial is preferred, falling back to
    volume GUID only when the serial is unavailable. This is not an anti-spoof
    security boundary, and a PnP ID can change when USB topology changes.
    """
    if not profile.enabled or candidate.bus_type != "USB":
        return False
    if not profile.disk_pnp_id or not candidate.disk_pnp_id:
        return False
    if profile.disk_pnp_id.casefold() != candidate.disk_pnp_id.casefold():
        return False
    if profile.volume_serial:
        return bool(candidate.volume_serial and
                    profile.volume_serial.casefold() == candidate.volume_serial.casefold())
    return bool(profile.volume_guid and candidate.volume_guid and
                profile.volume_guid.casefold() == candidate.volume_guid.casefold())


def choose_matches(profiles: list[Profile], volumes: list[UsbVolume]) -> dict[str, UsbVolume]:
    """Return one unambiguous mount for each profile; ambiguous matches are skipped."""
    result: dict[str, UsbVolume] = {}
    for profile in profiles:
        candidates = [v for v in volumes if same_device(profile, v)]
        if len(candidates) == 1:
            result[profile.id] = candidates[0]
    return result
