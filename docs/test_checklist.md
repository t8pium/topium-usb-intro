# Windows manual acceptance checklist (not yet performed)

Record OS build, Python/PySide6 version, USB enclosure model, filesystem, USB interface and observed logs. Do **not** claim completion based on unit tests alone.

- [ ] App starts on Windows 10/11 without elevation, shows tray and settings.
- [ ] Candidate physical USB external HDD appears, even if logical disk `DriveType=3` (fixed).
- [ ] Correct drive registration, original physical PnP ID and volume serial/GUID are captured.
- [ ] First launch with drive already attached shows no intro (default), unless opt-in enabled.
- [ ] Unplug and reconnect -> exactly one overlay, no duplicate on multiple WMI notifications.
- [ ] Infinite-loop GIF visually runs exactly one cycle; animation speed matches file metadata.
- [ ] Overlay fades/disappears, and Explorer opens the correct USB root **after** animation.
- [ ] Same drive attached under different Windows drive letter still triggers correctly.
- [ ] Unregistered USB drive, USB keyboard and internal disks never trigger the overlay.
- [ ] Rapid reconnect after confirmed removal triggers a fresh intro.
- [ ] Removal while animation plays doesn't open Explorer.
- [ ] Missing, malformed, oversized GIF falls back gracefully to sample.
- [ ] Root, one relative folder, multiple relative folders, nonexistent folder behaviors.
- [ ] `..`, absolute paths, `C:` drive redirects and symlink escapes cannot be opened.
- [ ] Pause, resume, Exit and system-tray menu work; no unintended extra Explorer windows.
- [ ] Opt-in autostart succeeds at sign-in and disables without leaving registry entry.
- [ ] `--demo` shows a GIF then opens a clearly labeled local demo folder.
- [ ] Config/log storage remains local, no network traffic/telemetry.
- [ ] Build `.exe`, launch it on a clean Windows machine and inspect PyInstaller assets.
- [ ] Low idle CPU/RAM during 30+ minutes; no zombie monitor threads after Exit.
