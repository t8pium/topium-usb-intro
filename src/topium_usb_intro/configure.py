"""Simple one-time setup: connected drive + selected GIF + enable task."""
from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QFileDialog, QLineEdit, QCheckBox, QSpinBox,
    QMessageBox, QGroupBox)

from .event_task import prepare_task_xml, run_elevated
from .gif_frames import load_one_cycle
from .models import Profile, UsbVolume
from .playback import Overlay
from .profiles import config_path, load_config, save_config
from .usb_monitor import DiskScan

LOG = logging.getLogger(__name__)


class SetupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TOPIUM USB INTRO — Setup")
        self.setMinimumWidth(560)
        self.setStyleSheet("""
            QWidget {font-size: 12px;}
            QGroupBox {font-weight: bold; border: 1px solid #777; border-radius: 6px;
                       margin-top: 15px; padding: 14px 10px 10px 10px;}
            QGroupBox::title {subcontrol-origin: margin; left: 12px; padding: 0 4px;}
            QPushButton {padding: 7px 12px;}
        """)
        try:
            self.config = load_config()
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Configuration invalid", str(exc))
            self.config = None
        self.scan: DiskScan | None = None
        self.volumes: list[UsbVolume] = []
        self.overlay = Overlay()
        main = QVBoxLayout(self)
        heading = QLabel("TOPIUM USB INTRO")
        heading.setStyleSheet("font-size: 22px; font-weight: bold;")
        main.addWidget(heading)
        main.addWidget(QLabel("Choose your already-connected USB drive, select a GIF, then enable automatic playback.\n"
                              "No TOPIUM program stays running after you close this window."))
        drive_box = QGroupBox("1. Select USB drive")
        drive_layout = QVBoxLayout(drive_box)
        selector = QHBoxLayout()
        self.drive_combo = QComboBox()
        self.drive_combo.setMinimumWidth(350)
        self.drive_combo.currentIndexChanged.connect(self.on_drive_selected)
        selector.addWidget(self.drive_combo, 1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_drives)
        selector.addWidget(refresh)
        drive_layout.addLayout(selector)
        main.addWidget(drive_box)

        gif_box = QGroupBox("2. Choose the welcome animation")
        gif_layout = QFormLayout(gif_box)
        gif_choice = QHBoxLayout()
        self.gif_path = QLineEdit()
        self.gif_path.setPlaceholderText("Leave blank for the bundled sample GIF")
        gif_choice.addWidget(self.gif_path)
        gif_button = QPushButton("Browse GIF")
        gif_button.clicked.connect(self.pick_gif)
        gif_choice.addWidget(gif_button)
        gif_layout.addRow("GIF file", gif_choice)
        self.nickname = QLineEdit()
        gif_layout.addRow("Drive nickname", self.nickname)
        self.position = QComboBox()
        self.position.addItem("Bottom-right", "bottom-right")
        self.position.addItem("Center", "center")
        gif_layout.addRow("Popup position", self.position)
        self.size = QSpinBox()
        self.size.setRange(64, 800)
        self.size.setValue(240)
        self.size.setSuffix(" px")
        gif_layout.addRow("Popup width", self.size)
        self.open_explorer = QCheckBox("Open this drive in File Explorer after the GIF")
        self.open_explorer.setChecked(True)
        gif_layout.addRow(self.open_explorer)
        main.addWidget(gif_box)

        controls = QHBoxLayout()
        preview = QPushButton("Preview GIF")
        preview.clicked.connect(self.preview_gif)
        controls.addWidget(preview)
        save = QPushButton("Save drive and GIF")
        save.clicked.connect(self.save)
        controls.addWidget(save)
        main.addLayout(controls)
        controls2 = QHBoxLayout()
        enable = QPushButton("Enable automatic intro")
        enable.setStyleSheet("font-weight: bold;")
        enable.clicked.connect(self.enable)
        controls2.addWidget(enable)
        disable = QPushButton("Disable automatic intro")
        disable.clicked.connect(self.disable)
        controls2.addWidget(disable)
        main.addLayout(controls2)
        self.status = QLabel("Connect your USB first. Nothing is installed until you enable automatic intro.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        note = QLabel("One-time Windows administrator approval is needed to enable Plug and Play event auditing "
                      "and create a scheduled task. The trigger requires Security event 6416 from your drive, "
                      "which must be tested on your laptop. The application itself uses 0 MB while idle.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 10px")
        main.addWidget(note)
        if self.config and self.config.profiles:
            self._load_profile(self.config.profiles[0])
        self.refresh_drives()

    def _load_profile(self, profile: Profile) -> None:
        self.nickname.setText(profile.name)
        self.gif_path.setText(profile.gif_path)
        self.size.setValue(profile.size)
        self.position.setCurrentIndex(max(0, self.position.findData(profile.position)))
        self.open_explorer.setChecked(profile.open_explorer)

    def refresh_drives(self) -> None:
        if self.scan is not None:
            return
        self.status.setText("Searching connected USB volumes...")
        self.scan = DiskScan()
        self.scan.complete.connect(self.on_scanned)
        self.scan.finished.connect(self.scan_finished)
        self.scan.start()

    def scan_finished(self) -> None:
        if self.scan is not None:
            self.scan.deleteLater()
            self.scan = None

    def on_scanned(self, volumes: list[UsbVolume], error: str) -> None:
        self.volumes = volumes
        self.drive_combo.blockSignals(True)
        self.drive_combo.clear()
        for vol in volumes:
            self.drive_combo.addItem(f"{vol.friendly_name} — {vol.disk_model}", vol)
        selected = self.config.profiles[0] if self.config and self.config.profiles else None
        if selected:
            for i, vol in enumerate(volumes):
                if (vol.disk_pnp_id.casefold() == selected.disk_pnp_id.casefold() and
                    vol.volume_serial.casefold() == selected.volume_serial.casefold()):
                    self.drive_combo.setCurrentIndex(i)
                    break
        self.drive_combo.blockSignals(False)
        if error:
            self.status.setText(error)
        elif not volumes:
            self.status.setText("No USB storage volume found. Plug in your drive, then select Refresh.")
        else:
            self.status.setText(f"Found {len(volumes)} connected USB volume(s). Select the right one.")
            self.on_drive_selected(self.drive_combo.currentIndex())

    def on_drive_selected(self, index: int) -> None:
        if index < 0 or not self.config:
            return
        vol: UsbVolume = self.drive_combo.itemData(index)
        if not vol:
            return
        matched = next((p for p in self.config.profiles if
                        p.disk_pnp_id.casefold() == vol.disk_pnp_id.casefold() and
                        p.volume_serial.casefold() == vol.volume_serial.casefold()), None)
        if matched:
            self._load_profile(matched)
        else:
            self.nickname.setText(vol.label or vol.disk_model or "My USB drive")

    def pick_gif(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select GIF", "", "GIF images (*.gif)")
        if path:
            self.gif_path.setText(path)

    def candidate(self, *, local_copy: bool) -> Profile:
        if not self.config:
            raise ValueError("Configuration is corrupted; back it up and repair before saving")
        vol = self.drive_combo.currentData()
        if not isinstance(vol, UsbVolume):
            raise ValueError("Select a currently connected USB drive first")
        profile = Profile.from_volume(vol, name=self.nickname.text().strip() or None)
        # Maintain a stable deduplication key if editing an existing profile.
        old = next((p for p in self.config.profiles if
                    p.disk_pnp_id.casefold() == profile.disk_pnp_id.casefold() and
                    p.volume_serial.casefold() == profile.volume_serial.casefold()), None)
        if old:
            profile.id = old.id
        profile.size = self.size.value()
        profile.position = self.position.currentData()
        profile.open_explorer = self.open_explorer.isChecked()
        selected = self.gif_path.text().strip()
        if selected:
            path = Path(selected)
            load_one_cycle(path)
            if path.stat().st_size > 30 * 1024 * 1024:
                raise ValueError("GIF exceeds 30 MB")
            if local_copy:
                sha = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                target = config_path().parent / "assets" / f"intro-{sha}.gif"
                target.parent.mkdir(parents=True, exist_ok=True)
                if path.resolve() != target.resolve():
                    shutil.copyfile(path, target)
                selected = str(target)
        profile.gif_path = selected
        return profile

    def preview_gif(self) -> None:
        try:
            self.overlay.play(self.candidate(local_copy=False))
            self.status.setText("Preview plays once; Explorer will not open.")
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Cannot preview", str(exc))

    def save(self) -> bool:
        try:
            profile = self.candidate(local_copy=True)
            self.config.profiles = [profile]
            self.config.autostart = False
            self.config.trigger_connected_on_startup = False
            save_config(self.config)
            self.gif_path.setText(profile.gif_path)
            self.status.setText("Saved. Click 'Enable automatic intro' for one-time Windows setup.")
            return True
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Could not save", str(exc))
            return False

    def enable(self) -> None:
        if not self.save():
            return
        response = QMessageBox.question(self, "One-time Windows setup",
            "Windows will request administrator approval to enable Plug and Play success-event auditing "
            "and create a Task Scheduler event trigger for TOPIUM USB INTRO.\n\n"
            "No custom process will stay running between insertions. Continue?")
        if response != QMessageBox.StandardButton.Yes:
            return
        try:
            path = prepare_task_xml()
            ok, message = run_elevated("install", str(path))
        except (ValueError, OSError) as exc:
            ok, message = False, str(exc)
        self.status.setText(message)
        if ok:
            QMessageBox.information(self, "Configured", "Task installed. Safely eject your drive, "
                                    "then reconnect it to test the automatic intro.")
        else:
            QMessageBox.warning(self, "Setup incomplete", message)

    def disable(self) -> None:
        response = QMessageBox.question(self, "Disable automatic intro",
            "Remove TOPIUM USB INTRO's scheduled task? This will not delete your GIF or settings. "
            "Plug and Play auditing will be left unchanged so other security policies are not affected.")
        if response != QMessageBox.StandardButton.Yes:
            return
        ok, message = run_elevated("remove")
        self.status.setText(message)
        if not ok:
            QMessageBox.warning(self, "Could not disable", message)
