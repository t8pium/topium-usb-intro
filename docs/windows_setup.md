# Windows installation and troubleshooting — v0.2.0

**For nonprogrammers:** Open the release `TOPIUM-USB-INTRO.exe`, choose a connected USB drive and GIF, preview it, then select Enable automatic intro and approve the Windows UAC prompt. Close the app, eject the drive, and reconnect.

**Event source:** Task Scheduler subscribes to Windows **Security** event ID **6416** (Audit PNP Activity). The subscription filters `EventData/ClassName=DiskDrive`; the task passes the event `DeviceId` into a short-lived Qt launcher. Both event ID and drive identification must work on your actual Windows build.

**If nothing happens:**

1. Verify the drive and GIF are saved in `%APPDATA%\TOPIUMUsbIntro\config.json` (do not share that file).
2. Open **Task Scheduler** and check `TOPIUM USB INTRO - On Connect` exists. It must run only when the original user is logged on, without elevated run level.
3. Open Event Viewer → Windows Logs → Security, filter on event 6416, reconnect drive and check if a new event appears. Some event logs require administrator permission to view.
4. In the event details, inspect `DeviceId` and `ClassName`. Compare DiskDrive DeviceId against the device in Device Manager or PowerShell `Get-CimInstance Win32_DiskDrive | Select-Object Model,PNPDeviceID,InterfaceType`. They must match for triggering. Do not share identifiers publicly.
5. Check `%APPDATA%\TOPIUMUsbIntro\app.log` for match/timeout/error messages. If there is no 6416 for each insertion, this mode cannot work on this system without a different, tested Windows trigger.
6. The compiled app copies itself to `%LOCALAPPDATA%\TOPIUMUsbIntro\bin\` at installation. This installed file must remain present.

**Disable:** Open the setup app and choose Disable automatic intro. This removes its scheduled task. It leaves Windows auditing unchanged and leaves user data untouched. Delete `%LOCALAPPDATA%\TOPIUMUsbIntro\bin\TOPIUM-USB-INTRO.exe` and `%APPDATA%\TOPIUMUsbIntro\` manually *after* removing the task if you also want to clear all local program files and settings.

**Build/source mode:** If you registered a scheduled task using a Python venv, keep the venv at the same absolute path. Re-run Enable if you move it. A source installation is not a published Windows binary.
