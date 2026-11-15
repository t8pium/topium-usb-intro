"""User-local, versioned configuration; written atomically."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from .models import Profile

CONFIG_VERSION = 1


def config_path() -> Path:
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ("AppData/Roaming" if os.name == "nt" else ".config")
    return root / "TOPIUMUsbIntro" / "config.json"


@dataclass
class AppConfig:
    profiles: list[Profile] = field(default_factory=list)
    monitoring_enabled: bool = True
    autostart: bool = False
    trigger_connected_on_startup: bool = False
    version: int = CONFIG_VERSION

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        if not isinstance(data, dict):
            raise ValueError("Configuration root must be an object")
        if data.get("version") != CONFIG_VERSION:
            raise ValueError(f"Unsupported configuration version {data.get('version')!r}")
        profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
        ids = [p.id for p in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate profile identifiers")
        return cls(
            profiles=profiles,
            monitoring_enabled=bool(data.get("monitoring_enabled", True)),
            autostart=bool(data.get("autostart", False)),
            trigger_connected_on_startup=bool(data.get("trigger_connected_on_startup", False)),
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "profiles": [p.to_dict() for p in self.profiles],
            "monitoring_enabled": self.monitoring_enabled,
            "autostart": self.autostart,
            "trigger_connected_on_startup": self.trigger_connected_on_startup,
        }


def load_config(path: Path | None = None) -> AppConfig:
    p = path or config_path()
    if not p.is_file():
        return AppConfig()
    return AppConfig.from_dict(json.loads(p.read_text(encoding="utf-8")))


def save_config(data: AppConfig, path: Path | None = None) -> None:
    p = path or config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=p.parent, prefix="config-",
                                suffix=".tmp", delete=False) as f:
            temp_name = f.name
            json.dump(data.to_dict(), f, indent=2)
            f.write("\n")
        os.replace(temp_name, p)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
