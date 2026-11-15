"""Reversible per-user Windows Run key. No administrator rights needed."""
from __future__ import annotations
import os
import subprocess
import sys

KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TOPIUMUsbIntro"


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        argv = [sys.executable]
    else:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        argv = [pythonw if os.path.isfile(pythonw) else sys.executable, "-m", "topium_usb_intro"]
    return subprocess.list2cmdline(argv)


def set_autostart(enabled: bool) -> None:
    if os.name != "nt":
        raise OSError("Windows autostart is unavailable on this OS")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
