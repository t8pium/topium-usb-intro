"""Settings and drive-registration interface (PySide6)."""
from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)
from .autostart import set_autostart
from .gif_frames import load_one_cycle
from .models import Profile, UsbVolume
from .profiles import config_path


class SettingsWindow(QMainWindow):
    def __init__(self, app_controller) -> None:
        super().__init__()
        self.controller = app_controller
        self.setWindowTitle("TOPIUM USB INTRO — Settings")
        self.resize(730, 785)
        self._editing_id: str | None = None
        shell = QWidget()
        self.setCentralWidget(shell)
        root = QVBoxLayout(shell)
        intro = QLabel("Register a USB hard drive, select a GIF, then connect it to play one intro.")
        intro.setWordWrap(True)
        root.addWidget(intro)

        device_box = QGroupBox("1 · Connected USB volumes")
        device_layout = QVBoxLayout(device_box)
        self.drives = QListWidget()
        self.drives.setMaximumHeight(118)
        device_layout.addWidget(self.drives)
        dbuttons = QHBoxLayout()
        scan_button = QPushButton("Refresh drives")
        scan_button.clicked.connect(self.controller.request_scan)
        add_button = QPushButton("Register selected drive")
        add_button.clicked.connect(self.add_profile)
        dbuttons.addWidget(scan_button)
        dbuttons.addWidget(add_button)
        device_layout.addLayout(dbuttons)
        root.addWidget(device_box)

        profile_box = QGroupBox("2 · Registered profiles")
        profile_layout = QVBoxLayout(profile_box)
        self.profiles = QListWidget()
        self.profiles.setMaximumHeight(96)
        self.profiles.currentItemChanged.connect(self.select_profile)
        profile_layout.addWidget(self.profiles)
        remove_button = QPushButton("Remove selected profile")
        remove_button.clicked.connect(self.remove_profile)
        profile_layout.addWidget(remove_button)
        root.addWidget(profile_box)

        options_box = QGroupBox("3 · Selected profile settings")
        options = QFormLayout(options_box)
        self.name_edit = QLineEdit()
        options.addRow("Drive nickname", self.name_edit)
        self.enabled = QCheckBox("Play intro on connection")
        self.enabled.setChecked(True)
        options.addRow("Enabled", self.enabled)
        gifrow = QHBoxLayout()
        self.gif_path = QLineEdit()
        self.gif_path.setPlaceholderText("Bundled sample animation")
        browse = QPushButton("Browse GIF")
        browse.clicked.connect(self.pick_gif)
        gifrow.addWidget(self.gif_path)
        gifrow.addWidget(browse)
        options.addRow("Animation", gifrow)
        self.mode = QComboBox()
        self.mode.addItem("Open the USB drive root", "root")
        self.mode.addItem("Open first existing specified folder", "first")
        self.mode.addItem("Open all existing specified folders", "multiple")
        options.addRow("Explorer target", self.mode)
        self.folders = QPlainTextEdit()
        self.folders.setPlaceholderText("Projects\nMedia\nWork\\Reports  (one relative path per line)")
        self.folders.setMaximumHeight(72)
        options.addRow("Relative folders", self.folders)
        self.explorer_toggle = QCheckBox("Launch File Explorer after the animation")
        self.explorer_toggle.setChecked(True)
        options.addRow("Explorer", self.explorer_toggle)
        self.size = QSpinBox()
        self.size.setRange(64, 800)
        self.size.setValue(240)
        self.size.setSuffix(" px wide")
        options.addRow("Popup size", self.size)
        self.position = QComboBox()
        self.position.addItem("Bottom-right", "bottom-right")
        self.position.addItem("Center", "center")
        options.addRow("Popup position", self.position)
        self.fade = QSpinBox()
        self.fade.setRange(0, 1500)
        self.fade.setValue(150)
        self.fade.setSuffix(" ms")
        options.addRow("Fade-out", self.fade)
        self.timeout = QSpinBox()
        self.timeout.setRange(500, 15000)
        self.timeout.setSingleStep(500)
        self.timeout.setValue(8000)
        self.timeout.setSuffix(" ms")
        options.addRow("Maximum playback", self.timeout)
        root.addWidget(options_box)

        general_box = QGroupBox("4 · Application")
        general = QVBoxLayout(general_box)
        self.monitoring = QCheckBox("Enable monitoring")
        self.monitoring.setChecked(self.controller.config.monitoring_enabled)
        self.startup = QCheckBox("Start at Windows user sign-in (optional)")
        self.startup.setChecked(self.controller.config.autostart)
        self.startup.setEnabled(os.name == "nt")
        self.startup_connected = QCheckBox("Also play intros for already connected drives on app startup")
        self.startup_connected.setChecked(self.controller.config.trigger_connected_on_startup)
        general.addWidget(self.monitoring)
        general.addWidget(self.startup)
        general.addWidget(self.startup_connected)
        root.addWidget(general_box)

        actions = QHBoxLayout()
        self.save_button = QPushButton("Save settings")
        self.save_button.clicked.connect(self.save)
        preview_button = QPushButton("Preview animation")
        preview_button.clicked.connect(self.preview)
        demo_button = QPushButton("Simulate USB connection")
        demo_button.clicked.connect(self.controller.simulate_insertion)
        actions.addWidget(self.save_button)
        actions.addWidget(preview_button)
        actions.addWidget(demo_button)
        root.addLayout(actions)
        self.status = QLabel("Ready. Settings and log stay on this computer.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.update_drives([])
        self.update_profiles()

    def update_drives(self, volumes: list[UsbVolume]) -> None:
        current = self.drives.currentItem()
        old_mount = current.data(Qt.ItemDataRole.UserRole).mount_point if current else ""
        self.drives.clear()
        for volume in volumes:
            summary = f"{volume.friendly_name}  |  {volume.disk_model}  |  ID …{volume.disk_pnp_id[-10:]}"
            item = QListWidgetItem(summary)
            item.setData(Qt.ItemDataRole.UserRole, volume)
            self.drives.addItem(item)
            if volume.mount_point == old_mount:
                self.drives.setCurrentItem(item)
        if self.drives.count() and not self.drives.currentItem():
            self.drives.setCurrentRow(0)
        if not volumes:
            self.status.setText("No confirmed USB storage volumes found. Connect a drive and select Refresh.")

    def update_profiles(self, select_id: str | None = None) -> None:
        selected = select_id or self._editing_id
        self.profiles.blockSignals(True)
        self.profiles.clear()
        for profile in self.controller.config.profiles:
            item = QListWidgetItem(f"{profile.name}  {'(paused)' if not profile.enabled else ''}")
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            self.profiles.addItem(item)
            if profile.id == selected:
                self.profiles.setCurrentItem(item)
        self.profiles.blockSignals(False)
        if self.profiles.currentItem():
            self.select_profile(self.profiles.currentItem(), None)
        elif self.profiles.count():
            self.profiles.setCurrentRow(0)
        else:
            self._editing_id = None
            self.name_edit.clear()

    def select_profile(self, current, previous) -> None:
        if current is None:
            self._editing_id = None
            return
        id_ = current.data(Qt.ItemDataRole.UserRole)
        profile = next((p for p in self.controller.config.profiles if p.id == id_), None)
        if profile is None:
            return
        self._editing_id = profile.id
        self.name_edit.setText(profile.name)
        self.enabled.setChecked(profile.enabled)
        self.gif_path.setText(profile.gif_path)
        self.mode.setCurrentIndex(max(0, self.mode.findData(profile.folder_mode)))
        self.folders.setPlainText("\n".join(profile.folders))
        self.explorer_toggle.setChecked(profile.open_explorer)
        self.size.setValue(profile.size)
        self.position.setCurrentIndex(max(0, self.position.findData(profile.position)))
        self.fade.setValue(profile.fade_ms)
        self.timeout.setValue(profile.max_duration_ms)

    def add_profile(self) -> None:
        item = self.drives.currentItem()
        if not item:
            QMessageBox.information(self, "Select a drive", "Connect your USB drive, refresh, then select it.")
            return
        volume: UsbVolume = item.data(Qt.ItemDataRole.UserRole)
        try:
            profile = Profile.from_volume(volume)
        except ValueError as exc:
            QMessageBox.warning(self, "Registration blocked", str(exc))
            return
        if any(p.disk_pnp_id.casefold() == profile.disk_pnp_id.casefold() and
               p.volume_serial.casefold() == profile.volume_serial.casefold() and
               p.volume_guid.casefold() == profile.volume_guid.casefold()
               for p in self.controller.config.profiles):
            QMessageBox.information(self, "Already registered", "This volume already has a profile.")
            return
        self.controller.config.profiles.append(profile)
        if not self.controller.persist(rebaseline=True):
            self.controller.config.profiles.remove(profile)
            return
        self.update_profiles(select_id=profile.id)
        self.status.setText("Drive registered. Configure its animation and save settings.")

    def remove_profile(self) -> None:
        if not self._editing_id:
            return
        old_profiles = self.controller.config.profiles.copy()
        self.controller.config.profiles = [p for p in self.controller.config.profiles
                                           if p.id != self._editing_id]
        if not self.controller.persist(rebaseline=True):
            self.controller.config.profiles = old_profiles
            self.status.setText("Removing the profile could not be saved.")
            return
        self._editing_id = None
        self.update_profiles()
        self.status.setText("Profile removed. Existing GIF files are left untouched.")

    def pick_gif(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select an animated GIF", "", "GIF images (*.gif)")
        if path:
            self.gif_path.setText(path)

    def _local_asset(self, selected: str) -> str:
        """Import a locally chosen GIF to AppData, decoupling it from USB arrival."""
        if not selected:
            return ""
        path = Path(selected)
        load_one_cycle(path)  # validate and cap resource usage before copying
        content = path.read_bytes()
        if len(content) > 30 * 1024 * 1024:
            raise ValueError("GIF file is too large (30 MB maximum)")
        suffix = hashlib.sha256(content).hexdigest()[:16]
        target = config_path().parent / "assets" / f"intro-{suffix}.gif"
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != target.resolve():
            shutil.copyfile(path, target)
        return str(target)

    def save(self) -> None:
        from .profiles import AppConfig
        snapshot = AppConfig.from_dict(self.controller.config.to_dict())
        autostart_changed = False
        profile = next((p for p in self.controller.config.profiles
                        if p.id == self._editing_id), None)
        try:
            if profile:
                if not self.name_edit.text().strip():
                    raise ValueError("Give the registered drive a nickname")
                profile.name = self.name_edit.text().strip()
                profile.gif_path = self._local_asset(self.gif_path.text().strip())
                profile.folder_mode = self.mode.currentData()
                profile.folders = [v.strip() for v in self.folders.toPlainText().splitlines() if v.strip()]
                # Check syntax without requiring the drive/folders to be connected.
                from pathlib import PureWindowsPath
                for folder in profile.folders:
                    p = PureWindowsPath(folder.replace("/", "\\"))
                    if folder.startswith(("/", "\\")) or p.is_absolute() or p.drive or ".." in p.parts or any(":" in x for x in p.parts):
                        raise ValueError(f"Folder must be a safe relative path: {folder!r}")
                profile.open_explorer = self.explorer_toggle.isChecked()
                profile.enabled = self.enabled.isChecked()
                profile.size = self.size.value()
                profile.position = self.position.currentData()
                profile.fade_ms = self.fade.value()
                profile.max_duration_ms = self.timeout.value()
            old_autostart = self.controller.config.autostart
            requested_autostart = self.startup.isChecked()
            if old_autostart != requested_autostart:
                set_autostart(requested_autostart)
                autostart_changed = True
            self.controller.config.autostart = requested_autostart
            self.controller.config.monitoring_enabled = self.monitoring.isChecked()
            self.controller.config.trigger_connected_on_startup = self.startup_connected.isChecked()
            if not self.controller.persist(rebaseline=True):
                self.controller.config = snapshot
                if autostart_changed:
                    try:
                        set_autostart(snapshot.autostart)
                    except OSError:
                        pass
                return
            self.update_profiles()
            self.status.setText("Settings saved. New arrivals use the updated profile.")
        except (ValueError, OSError) as exc:
            self.controller.config = snapshot
            if autostart_changed:
                try:
                    set_autostart(snapshot.autostart)
                except OSError:
                    pass
            QMessageBox.warning(self, "Could not save", str(exc))

    def preview(self) -> None:
        profile = next((p for p in self.controller.config.profiles
                        if p.id == self._editing_id), None)
        if profile is None:
            profile = Profile(name="Preview", disk_pnp_id="preview", volume_serial="preview",
                              volume_guid="")
        else:
            profile = Profile.from_dict(profile.to_dict())
        profile.gif_path = self.gif_path.text().strip()
        profile.position = self.position.currentData()
        profile.size = self.size.value()
        profile.fade_ms = self.fade.value()
        profile.max_duration_ms = self.timeout.value()
        self.controller.preview(profile)

    def closeEvent(self, event) -> None:
        if self.controller.tray and self.controller.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self.controller.shutdown()
            event.accept()
