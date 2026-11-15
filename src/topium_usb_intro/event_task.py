"""One-time Windows Task Scheduler integration (no resident custom monitor)."""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import ctypes
from ctypes import wintypes
from xml.etree import ElementTree as ET

from .profiles import config_path

TASK_NAME = "TOPIUM USB INTRO - On Connect"
PNP_GUID = "{0CCE9248-69AE-11D9-BED3-505054503030}"
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
ET.register_namespace("", NS)


def user_sid() -> str:
    """Resolve the SID of the *interactive* configuring user, before UAC elevation."""
    if os.name != "nt":
        raise OSError("Task Scheduler integration is Windows-only")
    result = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                            capture_output=True, text=True, check=True)
    row = next(csv.reader(io.StringIO(result.stdout)))
    sid = row[1].strip()
    if not sid.startswith("S-1-"):
        raise ValueError("Could not resolve current Windows user SID")
    return sid


def command_for_current_install() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve()), '--on-connect --event-device-id "$(deviceId)"'
    return str(Path(sys.executable).resolve()), '-m topium_usb_intro --on-connect --event-device-id "$(deviceId)"'


def stable_launcher_command() -> tuple[str, str]:
    """Keep the packaged exe outside Downloads so moving the original won't break it."""
    command, arguments = command_for_current_install()
    if not getattr(sys, "frozen", False):
        # Development installs use the active virtual environment, documented as such.
        return command, arguments
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise OSError("LOCALAPPDATA is not set; cannot install a stable launcher")
    target = Path(local) / "TOPIUMUsbIntro" / "bin" / "TOPIUM-USB-INTRO.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    if Path(command).resolve() != target.resolve():
        shutil.copy2(command, target)
    return str(target), arguments


def build_task_xml(sid: str, command: str, arguments: str) -> str:
    """Security/6416 emitted for newly recognized physical disk devices.

    On this trigger, a process runs *only* if the user is logged in and the event
    is recorded. The value query conveys which device triggered the task.
    """
    if not sid.startswith("S-1-") or not command:
        raise ValueError("A Windows user SID and absolute launcher command are required")
    if not PureWindowsPath(command).is_absolute():
        raise ValueError("Scheduled launcher must have an absolute path")
    task = ET.Element(f"{{{NS}}}Task", {"version": "1.4"})
    ET.SubElement(ET.SubElement(task, f"{{{NS}}}RegistrationInfo"), f"{{{NS}}}Description").text = (
        "Run TOPIUM USB INTRO briefly when Windows logs a USB storage-device recognition event."
    )
    triggers = ET.SubElement(task, f"{{{NS}}}Triggers")
    trigger = ET.SubElement(triggers, f"{{{NS}}}EventTrigger")
    ET.SubElement(trigger, f"{{{NS}}}Enabled").text = "true"
    query = ("<QueryList><Query Id=\"0\" Path=\"Security\"><Select Path=\"Security\">"
             "*[System[Provider[@Name='Microsoft-Windows-Security-Auditing'] and (EventID=6416)]] "
             "and *[EventData[Data[@Name='ClassName']='DiskDrive']]"
             "</Select></Query></QueryList>")
    ET.SubElement(trigger, f"{{{NS}}}Subscription").text = query
    values = ET.SubElement(trigger, f"{{{NS}}}ValueQueries")
    ET.SubElement(values, f"{{{NS}}}Value", {"name": "deviceId"}).text = (
        "Event/EventData/Data[@Name='DeviceId']"
    )
    principals = ET.SubElement(task, f"{{{NS}}}Principals")
    principal = ET.SubElement(principals, f"{{{NS}}}Principal", {"id": "Author"})
    ET.SubElement(principal, f"{{{NS}}}UserId").text = sid
    ET.SubElement(principal, f"{{{NS}}}LogonType").text = "InteractiveToken"
    ET.SubElement(principal, f"{{{NS}}}RunLevel").text = "LeastPrivilege"
    settings = ET.SubElement(task, f"{{{NS}}}Settings")
    for k, v in [
        ("MultipleInstancesPolicy", "IgnoreNew"),
        ("DisallowStartIfOnBatteries", "false"),
        ("StopIfGoingOnBatteries", "false"),
        ("AllowStartOnDemand", "true"),
        ("Enabled", "true"),
        ("Hidden", "false"),
        ("StartWhenAvailable", "false"),
        ("ExecutionTimeLimit", "PT2M"),
    ]:
        ET.SubElement(settings, f"{{{NS}}}{k}").text = v
    actions = ET.SubElement(task, f"{{{NS}}}Actions", {"Context": "Author"})
    action = ET.SubElement(actions, f"{{{NS}}}Exec")
    ET.SubElement(action, f"{{{NS}}}Command").text = command
    ET.SubElement(action, f"{{{NS}}}Arguments").text = arguments
    return '<?xml version="1.0" encoding="UTF-16"?>\n' + ET.tostring(task, encoding="unicode")


def prepare_task_xml() -> Path:
    """The setup UI creates this file before launching a one-time UAC helper."""
    command, arguments = stable_launcher_command()
    xml = build_task_xml(user_sid(), command, arguments)
    path = config_path().parent / "event_task.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-16")
    return path


def status_file() -> Path:
    return config_path().parent / "setup_result.json"


def _cmd(args: list[str]) -> tuple[bool, str]:
    process = subprocess.run(args, capture_output=True, text=True, errors="replace")
    return process.returncode == 0, (process.stdout + "\n" + process.stderr).strip()[-4000:]


def elevated_action(action: str, xml_file: str = "") -> int:
    """Only invoked explicitly by the settings GUI after UAC approval."""
    if os.name != "nt":
        return 2
    try:
        if action == "install":
            path = Path(xml_file)
            if not path.is_file() or path.parent != config_path().parent:
                raise ValueError("Refusing a task definition outside app configuration")
            # Enabling an existing Windows audit subcategory does not disable OS security.
            ok, message = _cmd(["auditpol.exe", "/set", f"/subcategory:{PNP_GUID}", "/success:enable"])
            if not ok:
                raise OSError("Could not enable Plug and Play event auditing: " + message)
            ok, message = _cmd(["schtasks.exe", "/Create", "/TN", TASK_NAME,
                                "/XML", str(path), "/F"])
            if not ok:
                raise OSError("Could not register task: " + message)
        elif action == "remove":
            ok, message = _cmd(["schtasks.exe", "/Delete", "/TN", TASK_NAME, "/F"])
            if not ok:
                raise OSError("Could not remove task: " + message)
        else:
            raise ValueError("Unsupported task operation")
        result = {"ok": True, "action": action, "message": "Task Scheduler updated successfully."}
    except Exception as exc:
        result = {"ok": False, "action": action, "message": str(exc)}
    try:
        status_file().write_text(json.dumps(result, indent=2), encoding="utf-8")
    except OSError:
        pass
    return 0 if result["ok"] else 1


def run_elevated(action: str, xml_file: str = "") -> tuple[bool, str]:
    """Request one-time Windows UAC; block for completion, then read result."""
    if os.name != "nt":
        return False, "Windows is required for event-triggered setup"
    # status is written by the process with administrator permission.
    try:
        status_file().unlink(missing_ok=True)
    except OSError:
        pass
    command, _ = command_for_current_install()
    # Build args by platform packaging mode; never execute content from USB.
    import subprocess as _sp
    parameters = (["--task-admin", action] if getattr(sys, "frozen", False)
                  else ["-m", "topium_usb_intro", "--task-admin", action])
    if xml_file:
        parameters.extend(["--task-xml", xml_file])
    # ShellExecuteExW with SEE_MASK_NOCLOSEPROCESS allows us to collect the real
    # child exit code instead of claiming success just because UAC opened.
    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = command
    info.lpParameters = _sp.list2cmdline(parameters)
    info.nShow = 0  # SW_HIDE for packaged windowless helper
    shell = ctypes.windll.shell32
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        return False, "Windows elevation was cancelled or failed."
    try:
        ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 60000)
        exit_code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code))
    finally:
        ctypes.windll.kernel32.CloseHandle(info.hProcess)
    if status_file().exists():
        try:
            data = json.loads(status_file().read_text(encoding="utf-8"))
            return bool(data["ok"]), str(data["message"])
        except (ValueError, OSError, KeyError):
            pass
    return False, "Setup did not report success. Check Windows Task Scheduler (exit code: %s)." % exit_code.value
