# TOPIUM USB INTRO v0.2.0 — verification ledger

## New requested behavior

The app must run only on one user's Windows computer. The user should download a ready EXE from a GitHub release, open a GUI, select an already-connected USB disk, choose a GIF, save and enable automatic playback on future insertions, **without a continuous background process**.

## Implemented in source

- New `configure.py` setup GUI and `__main__.py` entrypoint; source v0.2.0 no longer starts the resident WMI watcher/tray.
- New `event_task.py` generates an interactive, least-privilege Windows scheduled task for Security event 6416 / DiskDrive class; passes the event DeviceId; allows UAC-elevated one-time task installation and removal; opt-in PnP success auditing; preserves audit setting on uninstall.
- New `one_shot.py` verifies event physical DiskDrive identity and a registered USB volume, waits for mount readiness, protects against duplicate events, plays the GIF exactly once, opens Explorer and exits.
- New `event_match.py` pure matching/debounce logic and `test_event_task.py` tests.
- For frozen builds, installer copies the current standalone EXE into LocalAppData before registering task, so deleting the initial Downloads copy does not break the task.
- GitHub Actions Windows test/build and tag-based release workflows; Windows PyInstaller build script.

## Verification

- Executed on Linux with Python 3.13: `python -m pytest -q`: **45 passed, 1 skipped**; the skip covers native Qt integration because PySide6 is absent.
- `python -m compileall -q src tests scripts`: **passed**.
- Task XML tested by round-trip Python XML parser, not by Windows Task Scheduler itself.
- No physical USB insertion, Security Event 6416, Windows UAC/task installation, visible GIF on Windows, Windows PyInstaller exe build, or GitHub workflow/release run in this environment.
- Therefore Windows usability, event reliability, standalone binary and direct GitHub download **are not verified or published**.

## Specific risks

1. Event ID 6416 may not be emitted for every physical USB reconnect on a particular Windows build, policy or USB bridge. The implementation must not be represented as universally reliable before testing the target laptop.
2. Event 6416's `DeviceId` must correspond to `Win32_DiskDrive.PNPDeviceID`. A SCSI/UASP bridge may expose changing IDs or other event variants; fail closed.
3. One-time UAC/system audit configuration affects Windows auditing globally; the app asks first, never disables audit policy on uninstall.
4. Onefile executable extraction adds startup latency; no idle custom RAM consumption.
5. A second task trigger during the intro is suppressed by task setting and a short persistent 5s throttle; very rapid unplug/replug can be missed.
6. The source repository retains unused v0.1.0 watcher modules to preserve tests; they are never imported by the v0.2.0 entrypoint.

## Release gates

- Successful Windows Actions build and artifact attached.
- Verified install/disable from a normal non-elevated GUI with one-time UAC confirmation.
- 10 physical insertions, after reboot, same and different ports; one intro per insertion.
- Verified no intro for unrelated USB devices; missing GIF and unplug-during-playback behavior.
- Push repository to GitHub, run CI, tag release, verify downloadable Windows EXE.
