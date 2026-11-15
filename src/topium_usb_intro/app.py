"""Connect the Windows watcher, UI, GIF overlay and Explorer safely."""
from __future__ import annotations
import logging
import os
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon
from .explorer import folders_to_open, open_folders
from .models import Profile, UsbVolume, choose_matches
from .playback import Overlay
from .profiles import AppConfig, load_config, save_config
from .settings_ui import SettingsWindow
from .state import SessionTracker
from .usb_monitor import DiskScan, VolumeMonitor

LOG = logging.getLogger(__name__)


@dataclass
class PlayRequest:
    profile: Profile
    volume: UsbVolume | None
    is_demo: bool = False


class Controller(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        try:
            self.config: AppConfig = load_config()
        except Exception as exc:
            # Keep invalid configuration untouched for manual recovery.
            LOG.exception("Unable to load configuration")
            self.config = AppConfig()
            self._config_error = str(exc)
        else:
            self._config_error = ""
        self.volumes: list[UsbVolume] = []
        self.tracker = SessionTracker()
        self._scan: DiskScan | None = None
        self._scan_pending = False
        self._scan_confirmed_removal = False
        self._scan_first = True
        self._monitor: VolumeMonitor | None = None
        self._stopping = False
        self.queue: deque[PlayRequest] = deque()
        self.current: PlayRequest | None = None
        self.overlay = Overlay()
        self.overlay.completed.connect(self._after_animation)
        self.window = SettingsWindow(self)
        self.tray: QSystemTrayIcon | None = None
        self._init_tray()
        self._fallback = QTimer(self)
        self._fallback.setInterval(60_000)
        self._fallback.timeout.connect(self.request_scan)
        self._fallback.start()
        self.request_scan()
        if not self.config.profiles or self._config_error or self.tray is None:
            self.window.show()
            if self._config_error:
                QMessageBox.warning(self.window, "Configuration could not load",
                                    "Settings could not be read. Original config was not overwritten.\n" +
                                    self._config_error)

    def _init_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = QPixmap(64, 64)
        icon.fill(QColor(0, 0, 0, 0))
        painter = QPainter(icon)
        painter.setBrush(QColor(50, 160, 230))
        painter.setPen(QColor(220, 240, 255))
        painter.drawRoundedRect(4, 4, 56, 56, 15, 15)
        painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "T")
        painter.end()
        tray = QSystemTrayIcon(QIcon(icon), self.app)
        tray.setToolTip("TOPIUM USB INTRO")
        menu = QMenu()
        action_settings = QAction("Open Settings", menu)
        action_settings.triggered.connect(self.show_settings)
        action_preview = QAction("Test Animation", menu)
        action_preview.triggered.connect(lambda: self.preview(self._example_profile()))
        action_pause = QAction("Pause Monitoring", menu)
        action_pause.setCheckable(True)
        action_pause.setChecked(not self.config.monitoring_enabled)
        action_pause.triggered.connect(self._toggle_pause)
        action_exit = QAction("Exit", menu)
        action_exit.triggered.connect(self.shutdown)
        for action in (action_settings, action_preview, action_pause, action_exit):
            menu.addAction(action)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: self.show_settings()
                               if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        tray.show()
        self.tray = tray
        self.app.setQuitOnLastWindowClosed(False)

    def _example_profile(self) -> Profile:
        return self.config.profiles[0] if self.config.profiles else Profile(
            name="Sample", disk_pnp_id="demo", volume_serial="demo", volume_guid="")

    def _toggle_pause(self, paused: bool) -> None:
        self.config.monitoring_enabled = not paused
        self.persist(rebaseline=True)
        self.window.monitoring.setChecked(not paused)

    def show_settings(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def persist(self, *, rebaseline: bool = False) -> bool:
        try:
            # If the load previously failed, don't silently replace the corrupt source.
            if self._config_error:
                raise ValueError("Existing configuration is invalid; back it up before saving changes")
            save_config(self.config)
        except Exception as exc:
            LOG.error("Cannot persist configuration: %s", type(exc).__name__)
            QMessageBox.warning(self.window, "Saving failed", str(exc))
            return False
        if rebaseline:
            self.tracker.rebaseline(set(choose_matches(self.config.profiles, self.volumes)))
        return True

    def request_scan(self, confirmed_removal: bool = False) -> None:
        if self._stopping:
            return
        self._scan_confirmed_removal |= confirmed_removal
        if self._scan is not None:
            self._scan_pending = True
            return
        scan = DiskScan()
        self._scan = scan
        scan.complete.connect(self._on_scan)
        scan.finished.connect(self._scan_finished)
        scan.start()

    def _scan_finished(self) -> None:
        if self._scan is not None:
            self._scan.deleteLater()
            self._scan = None
        if self._scan_pending and not self._stopping:
            self._scan_pending = False
            self.request_scan()

    def _on_scan(self, volumes: list[UsbVolume], error: str) -> None:
        if self._stopping:
            return
        if error:
            LOG.warning("Enumeration: %s", error)
            self.window.status.setText(error)
        else:
            self.volumes = volumes
            self.window.update_drives(volumes)
            matched = choose_matches(self.config.profiles, volumes)
            arrivals = self.tracker.observe(
                set(matched),
                allow_initial=self.config.trigger_connected_on_startup,
                confirmed_removal=self._scan_confirmed_removal,
            )
            for profile_id in arrivals:
                if self.config.monitoring_enabled:
                    profile = next((p for p in self.config.profiles if p.id == profile_id), None)
                    if profile:
                        self.queue.append(PlayRequest(profile, matched[profile_id]))
            self._show_next()
        self._scan_confirmed_removal = False
        if self._scan_first:
            self._scan_first = False
            self._start_monitor()

    def _start_monitor(self) -> None:
        if os.name != "nt":
            return
        mon = VolumeMonitor()
        self._monitor = mon
        mon.changed.connect(self._volume_changed)
        mon.failed.connect(self._watcher_failed)
        mon.start()

    def _volume_changed(self, removed: bool) -> None:
        self._scan_confirmed_removal |= removed
        QTimer.singleShot(850, lambda: self.request_scan(removed))

    def _watcher_failed(self, error: str) -> None:
        LOG.warning("Volume monitor stopped: %s", error)
        self.window.status.setText(error + "; using periodic scan fallback")
        self._fallback.setInterval(8000)

    def preview(self, profile: Profile) -> None:
        # No Explorer access for the preview-only action.
        self.queue.append(PlayRequest(profile, None))
        self._show_next()

    def simulate_insertion(self) -> None:
        """End-to-end simulation with an explicitly fake USB volume, no real hardware."""
        root = Path(tempfile.gettempdir()) / "TOPIUMUsbIntro-Demo"
        root.mkdir(exist_ok=True)
        readme = root / "ABOUT_THIS_SIMULATION.txt"
        if not readme.exists():
            readme.write_text(
                "This is a simulated USB volume created by TOPIUM USB INTRO.\n"
                "No actual USB drive was connected or verified.\n", encoding="utf-8")
        profile = Profile.from_dict(self._example_profile().to_dict())
        profile.open_explorer = True
        profile.folder_mode = "root"
        fake = UsbVolume(disk_pnp_id="USBSTOR\\TOPIUM_DEMO", disk_serial="SIMULATED",
                         disk_model="TOPIUM simulated USB", volume_serial="SIM1",
                         volume_guid="\\\\?\\Volume{TOPIUM-DEMO}\\",
                         mount_point=str(root), label="DEMO")
        self.queue.append(PlayRequest(profile, fake, is_demo=True))
        self.window.status.setText("Simulating arrival: animation → demo folder. No physical USB checked.")
        self._show_next()

    def _show_next(self) -> None:
        if self.current is not None or not self.queue:
            return
        self.current = self.queue.popleft()
        self.overlay.play(self.current.profile)

    def _after_animation(self) -> None:
        request = self.current
        self.current = None
        if request and request.volume and request.profile.open_explorer:
            if not request.is_demo and not any(
                p.id == request.profile.id and p.enabled for p in self.config.profiles
            ):
                QTimer.singleShot(0, self._show_next)
                return
            volume = request.volume
            if not request.is_demo:
                # Resolve the current mount from the latest scan, not a saved drive letter.
                new = choose_matches([request.profile], self.volumes).get(request.profile.id)
                if new is None:
                    volume = None
                else:
                    volume = new
            if volume and volume.mount.is_dir():
                targets = folders_to_open(request.profile, volume.mount)
                errors = open_folders(targets)
                for error in errors:
                    LOG.warning("Explorer: %s", error)
                if errors:
                    self.window.status.setText("; ".join(errors))
            else:
                LOG.info("Drive removed during animation, skipping Explorer")
        QTimer.singleShot(0, self._show_next)

    def shutdown(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        self._fallback.stop()
        self.overlay.finish(emit=False)
        if self._monitor:
            self._monitor.stop()
            if not self._monitor.wait(1800):
                LOG.warning("WMI watcher didn't stop before quit")
        if self._scan:
            self._scan.wait(3000)
        if self.tray:
            self.tray.hide()
        self.app.quit()
