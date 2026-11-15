"""Fail-closed folder selection and safe Explorer invocation."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path, PureWindowsPath
from .models import Profile


class UnsafeFolder(ValueError):
    pass


def safe_relative_directory(root: Path, relative: str) -> Path:
    """Reject absolute/UNC/parent escapes and symlinks leading outside root."""
    text = relative.strip().replace("/", "\\")
    parts = PureWindowsPath(text)
    if not text or text.startswith("\\") or parts.is_absolute() or parts.drive or ".." in parts.parts:
        raise UnsafeFolder(f"Unsafe relative folder: {relative!r}")
    if any(":" in part for part in parts.parts):
        raise UnsafeFolder("Alternate data streams and drive prefixes are not allowed")
    base = root.resolve(strict=True)
    proposed = base.joinpath(*parts.parts)
    resolved = proposed.resolve(strict=True)
    if not resolved.is_relative_to(base):
        raise UnsafeFolder("The folder resolves outside the selected volume")
    if not resolved.is_dir():
        raise UnsafeFolder("Requested target is not a directory")
    return resolved


def folders_to_open(profile: Profile, mount: Path) -> list[Path]:
    """Return valid paths; missing subfolders are skipped, not fatal."""
    if not mount.is_dir():
        return []
    if profile.folder_mode == "root":
        return [mount.resolve()]
    valid: list[Path] = []
    for folder in profile.folders:
        try:
            resolved = safe_relative_directory(mount, folder)
        except (UnsafeFolder, OSError, RuntimeError):
            continue
        if resolved not in valid:
            valid.append(resolved)
        if profile.folder_mode == "first":
            break
    return valid


def open_folders(paths: list[Path]) -> list[str]:
    """No shell=True, no user-supplied command line; return human-readable errors."""
    errors: list[str] = []
    for path in paths:
        if not path.is_dir():
            errors.append(f"Folder no longer exists: {path}")
            continue
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer.exe", str(path)], shell=False)
            else:
                # Simulation on macOS/Linux is for development only.
                errors.append("Explorer launch is Windows-only")
        except OSError as error:
            errors.append(f"Explorer could not open {path}: {error}")
    return errors
