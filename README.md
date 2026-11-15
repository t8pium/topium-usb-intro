# TOPIUM USB INTRO — v0.2.0 (event-triggered)

Personalized GIF welcome overlay for **one registered USB drive on your own Windows 10/11 laptop**. Register the drive while it is **already connected**, select a GIF, and click **Enable automatic intro**. On a qualifying future insertion Windows starts a brief helper, plays the GIF **once**, optionally opens the drive's File Explorer window, then exits.

**No TOPIUM background monitor, startup tray process, continuous polling, or idle custom-program RAM usage.** Windows' built-in Task Scheduler performs event triggering. **Windows CI built an executable successfully and passed its automated tests. The physical USB insertion trigger and visible GIF playback have not yet been verified on a user's laptop.**

## What the app looks like to a user

1. Download [**TOPIUM-USB-INTRO.exe (v0.2.0-beta.1)**](https://github.com/t8pium/topium-usb-intro/releases/download/v0.2.0-beta.1/TOPIUM-USB-INTRO.exe) from the verified GitHub beta release. It is a graphical Windows app; Python is *not* required to run the compiled executable.
2. Double-click the EXE. Attach your USB drive **before opening the program** if you want it to appear in the selector.
3. Choose the matching USB drive (model, label and drive letter displayed), click **Browse GIF**, and optionally set animation size/placement.
4. Click **Preview GIF** to verify the animation without launching Explorer.
5. Click **Enable automatic intro**. The program saves your choice, copies the bundled single EXE into `%LOCALAPPDATA%\TOPIUMUsbIntro\bin\` so the task doesn't depend on the Downloads folder, asks for **one-time UAC approval**, enables Windows **Audit PNP Activity success** if needed, and registers a Task Scheduler event trigger.
6. Close the app: no custom process remains. Safely eject/unplug your drive and reconnect it **while logged into your desktop**. If your system emits the required event, the animation plays and the Explorer window opens.
7. To change drives or GIFs, reopen the EXE and save again. To stop triggering, click **Disable automatic intro**; it removes the task, leaving your GIF and other Windows auditing settings unchanged.

**Important:** The **Windows EXE is now downloadable** from the [beta release](https://github.com/t8pium/topium-usb-intro/releases/tag/v0.2.0-beta.1). Windows CI passed the automated tests and compiled the executable. Actual physical USB reconnection and animated desktop playback remain **untested**; this is a beta, not hardware-certified.

### How it works

```text
Device connects
  -> Windows Security event 6416 (Audit Plug and Play success; ClassName=DiskDrive)
  -> built-in Windows Task Scheduler launches a *transient* instance
  -> validates the event's DeviceId against the registered Win32_DiskDrive PNPDeviceID
  -> waits until the registered volume (physical ID + volume serial) is mounted
  -> plays user-selected local GIF exactly once (short transparent Qt overlay)
  -> verifies mount again and opens File Explorer
  -> application terminates, all its RAM released
```

This **does not** continuously use Python/WMI to watch drives. It does require Windows event auditing and a scheduled task configured once on your own PC. A short 5-second duplicate-event throttle prevents double playback; reinsertion within that period may be skipped. Security event 6416's availability and DeviceId matching vary with hardware and Windows policies. **We cannot guarantee the event is generated for every connection before Windows hardware testing.**

### Personalization

- Select a USB that is presently connected and recognized as physical USB storage (including external HDDs reported as fixed disks).
- Match by physical DiskDrive PnP ID + filesystem volume serial rather than drive letter or label alone.
- Choose your GIF; it is validated and copied into your user profile. No executing untrusted programs from the inserted drive.
- GIF frame delays and one-loop playback are enforced, including GIF files whose metadata requests infinite looping. Size, position and Explorer launch are configurable.
- Leave the GIF blank for a bundled original sample. A corrupt/missing GIF falls back to the bundled sample.
- Multiple subfolder mode remains available in the underlying profile model for possible future UI expansion; v0.2.0 GUI opens the root folder by default.

### Changes and privileges

- The **Enable automatic intro** button explicitly asks for consent and one-time administrator elevation.
- It uses `auditpol /set /subcategory:{0CCE9248-69AE-11D9-BED3-505054503030} /success:enable` to enable the existing Windows PnP audit category; it does not disable security controls.
- It installs `TOPIUM USB INTRO - On Connect` as a Windows Task Scheduler task subscribed to Security Event ID `6416` with disk class `DiskDrive`.
- The task runs as the **original interactive user**, at **least privilege**, only while that user is logged in. The UAC helper exists only during setup.
- Uninstalling/removing the task intentionally does **not** reset auditing: other software or administrators may depend on it.
- Config: `%APPDATA%\TOPIUMUsbIntro\config.json` (private device identifiers; do not publish). Copied GIFs in `%APPDATA%\TOPIUMUsbIntro\assets`. EXE when compiled in `%LOCALAPPDATA%\TOPIUMUsbIntro\bin`. No telemetry, ad network, API keys or cloud service.

### Limits

- **Windows only**, **your laptop only**, signed-in interactive desktop only. No automatic execution on another, unconfigured PC.
- If Audit PNP Activity isn't allowed by group policy or this disk doesn't emit a matching `6416` on insertion, the event-triggered workflow won't work. A hardware-specific alternative trigger must then be tested and configured; it is **not implemented here**.
- If Windows assigns a different drive letter, matching should still work when the physical and volume IDs remain stable. If the USB bridge changes its PnP ID with a port/driver change, re-registration may be required.
- A locked desktop won't show the overlay on the lock screen. Windows execution restrictions and SmartScreen may also affect setup.
- PyInstaller `--onefile` has an extraction/startup overhead, so the popup will not necessarily appear instantaneously.
- Already-connected drives do **not** trigger on saving; safely remove and reconnect to produce a new event.
- The original v0.1.0 tray/WMI-watch mode source modules remain in the repository for test compatibility but **are never launched by the v0.2.0 entrypoint**.

## Run from source (Windows)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m topium_usb_intro --settings
.\.venv\Scripts\python.exe -m pytest -q
```

In development/source mode, the scheduled task uses the Python interpreter from the virtual environment. Do not delete or move that venv after registering the task. For non-programmers, use a release EXE instead.

## Build Windows EXE

On a **Windows 10/11 machine**:

```powershell
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1
```

Expected output: `dist\TOPIUM-USB-INTRO.exe`. **GitHub Actions completed the Windows EXE build and automated test suite successfully** on 15 Nov 2026. The physical USB insertion test has not been run. The current downloadable binary is a [v0.2.0-beta.1 pre-release](https://github.com/t8pium/topium-usb-intro/releases/tag/v0.2.0-beta.1); the source-based Windows build instructions are still available for independent reproduction.

## Test before distributing

1. Confirm a physical USB insertion creates a **Security/6416** event with `ClassName=DiskDrive` and a `DeviceId` matching its `Win32_DiskDrive.PNPDeviceID`.
2. With the task registered and the setup app closed, disconnect and reconnect the drive 10 times, including after a laptop restart. Check whether each event starts exactly one overlay and opens Explorer once.
3. Try a different drive; it must not trigger playback. Test changing drive letters, USB ports, USB HDDs exposed via USB-SATA/SCSI bridge, and removal during the intro.
4. Verify Windows Task Scheduler shows the task with `Run only when user is logged on` and that no TOPIUM process remains when idle.
5. Test both enable and disable and inspect logs in `%APPDATA%\TOPIUMUsbIntro\`.

## GitHub repository and binary release

- [GitHub repository](https://github.com/t8pium/topium-usb-intro)
- [Download TOPIUM-USB-INTRO.exe](https://github.com/t8pium/topium-usb-intro/releases/download/v0.2.0-beta.1/TOPIUM-USB-INTRO.exe)
- [Windows build history](https://github.com/t8pium/topium-usb-intro/actions)

The beta binary was compiled on a GitHub-hosted Windows runner and is not code-signed. SmartScreen may display a warning. Verify the source and publisher before granting any requested UAC approval; the UAC step is only for registering the scheduled task and enabling device-event auditing.

## Security and references

The executable is locally installed and launches only in response to configured Windows events. It never executes contents of the USB drive, changes AutoRun restrictions, installs a privileged daemon, or runs continuously. Treat untrusted GIFs and downloaded executables cautiously. To distribute to others, consider code-signing the binary.

- [Microsoft: Audit PNP Activity](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/audit-pnp-activity)
- [Microsoft: Security event 6416](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-6416)
- [Microsoft: Task Scheduler EventTrigger schema](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-eventtrigger-triggergroup-element)
- [Microsoft: Schtasks create](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create)

MIT licensed. See [BUILD_REPORT.md](BUILD_REPORT.md) for the exact testing record.
