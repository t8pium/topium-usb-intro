"""Per-insertion one-shot launcher. Exits after the GIF; never stays resident."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from PySide6.QtCore import QObject, QTimer
from .explorer import folders_to_open, open_folders
from .event_match import event_matches_profile, should_play
from .models import Profile, same_device
from .playback import Overlay
from .profiles import config_path, load_config
from .usb_monitor import enumerate_usb_volumes

LOG = logging.getLogger(__name__)




class SingleProcessLock:
    """One instant of the helper at once; Windows file locks vanish on exit."""
    def __init__(self) -> None:
        self.fd: int | None = None

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        import msvcrt
        path = config_path().parent / "active.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.lseek(self.fd, 0, os.SEEK_SET)
            msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            os.close(self.fd)
            self.fd = None
            return False

    def release(self) -> None:
        if self.fd is not None:
            import msvcrt
            try:
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            finally:
                os.close(self.fd)
                self.fd = None


class OneShot(QObject):
    def __init__(self, app, event_device_id: str):
        super().__init__()
        self.app = app
        self.event_device_id = event_device_id
        self.lock = SingleProcessLock()
        self.profile: Profile | None = None
        self.overlay: Overlay | None = None
        self.deadline = time.monotonic() + 18
        self._played = False
        QTimer.singleShot(0, self.begin)

    def quit(self) -> None:
        self.lock.release()
        self.app.quit()

    def begin(self) -> None:
        if not self.lock.acquire():
            LOG.info("Another TOPIUM intro is already in progress")
            self.app.quit()
            return
        try:
            config = load_config()
            candidates = [p for p in config.profiles if p.enabled and
                          event_matches_profile(self.event_device_id, p)]
            if not candidates:
                LOG.info("Event does not match a registered physical USB disk")
                self.quit()
                return
            self.profile = candidates[0]
            self.wait_for_mount()
        except Exception:
            LOG.exception("Unable to start transient intro")
            self.quit()

    def wait_for_mount(self) -> None:
        assert self.profile is not None
        try:
            volumes = enumerate_usb_volumes()
            matches = [v for v in volumes if same_device(self.profile, v)]
            if len(matches) == 1 and Path(matches[0].mount_point).is_dir():
                if not self._reserve_play():
                    self.quit()
                    return
                self.overlay = Overlay()
                self.overlay.completed.connect(self.finish)
                self._played = True
                self.overlay.play(self.profile)
                return
        except Exception:
            LOG.warning("Volume not ready yet", exc_info=True)
        if time.monotonic() < self.deadline:
            QTimer.singleShot(700, self.wait_for_mount)
        else:
            LOG.warning("Timed out waiting for registered USB mount")
            self.quit()

    def _reserve_play(self) -> bool:
        assert self.profile is not None
        record = config_path().parent / "last_play.json"
        try:
            state = json.loads(record.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        now = time.time()
        previous = float(state.get(self.profile.id, 0))
        if not should_play(now, previous):
            LOG.info("Suppressing duplicate insertion notification")
            return False
        state[self.profile.id] = now
        try:
            record.write_text(json.dumps(state), encoding="utf-8")
        except OSError:
            LOG.warning("Could not persist anti-duplicate state")
        return True

    def finish(self) -> None:
        if self._played and self.profile and self.profile.open_explorer:
            try:
                # Re-enumerate to avoid opening a stale mount after unplugging.
                matches = [v for v in enumerate_usb_volumes() if same_device(self.profile, v)]
                if len(matches) == 1:
                    errors = open_folders(folders_to_open(self.profile, Path(matches[0].mount_point)))
                    if errors:
                        LOG.warning("Explorer launch: %s", errors)
            except Exception:
                LOG.exception("Unable to open USB volume")
        self.quit()
