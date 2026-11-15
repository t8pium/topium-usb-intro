"""Windows WMI event monitor and USB storage enumerator, isolated from the UI."""
from __future__ import annotations
import logging
import os
from PySide6.QtCore import QThread, Signal
from .models import UsbVolume

LOG = logging.getLogger(__name__)


def enumerate_usb_volumes() -> list[UsbVolume]:
    """Find logical volumes attached to confirmed physical USB disks.

    Win32_DiskDrive association chain accounts for HDDs flagged as fixed disks.
    MSFT_Disk.BusType=7 is authoritative when exposed by Windows Storage WMI;
    Win32_DiskDrive.InterfaceType/USBSTOR is a documented fallback.
    """
    if os.name != "nt":
        return []
    import ctypes
    import wmi
    c = wmi.WMI(namespace=r"root\cimv2")
    bus_by_index: dict[int, int] = {}
    try:
        storage = wmi.WMI(namespace=r"root\Microsoft\Windows\Storage")
        for disk in storage.MSFT_Disk():
            bus_by_index[int(disk.Number)] = int(disk.BusType)
    except Exception:
        LOG.info("Storage MSFT_Disk BusType unavailable; using disk interface fallback")

    def volume_guid(letter: str) -> str:
        buf = ctypes.create_unicode_buffer(1024)
        try:
            ok = ctypes.windll.kernel32.GetVolumeNameForVolumeMountPointW(letter, buf, len(buf))
            return buf.value if ok else ""
        except (OSError, AttributeError):
            return ""

    results: list[UsbVolume] = []
    for disk in c.Win32_DiskDrive():
        try:
            index = int(disk.Index)
            pnp = str(disk.PNPDeviceID or "")
            fallback_usb = str(disk.InterfaceType or "").upper() == "USB" or pnp.upper().startswith("USBSTOR\\")
            bus = bus_by_index.get(index)
            is_usb = bus == 7 if bus is not None else fallback_usb
            if not is_usb:
                continue
            for part in disk.associators(wmi_result_class="Win32_DiskPartition"):
                for logical in part.associators(wmi_result_class="Win32_LogicalDisk"):
                    letter = str(logical.DeviceID or "")
                    if len(letter) != 2 or letter[1] != ":":
                        continue
                    results.append(UsbVolume(
                        disk_pnp_id=pnp,
                        disk_serial=str(disk.SerialNumber or "").strip(),
                        disk_model=str(disk.Model or ""),
                        volume_serial=str(logical.VolumeSerialNumber or ""),
                        volume_guid=volume_guid(letter + "\\"),
                        mount_point=letter + "\\",
                        disk_index=index,
                        bus_type="USB",
                        label=str(logical.VolumeName or ""),
                    ))
        except Exception as exc:
            LOG.warning("Unable to inspect one physical disk: %s", type(exc).__name__)
    return results


class DiskScan(QThread):
    complete = Signal(object, str)

    def run(self) -> None:
        if os.name != "nt":
            self.complete.emit([], "Windows USB detection is unavailable on this OS")
            return
        import pythoncom
        pythoncom.CoInitialize()
        try:
            self.complete.emit(enumerate_usb_volumes(), "")
        except Exception as exc:
            LOG.exception("Volume enumeration failed")
            self.complete.emit([], f"USB scan failed: {exc}")
        finally:
            pythoncom.CoUninitialize()


class VolumeMonitor(QThread):
    changed = Signal(bool)  # True means a removal notification occurred
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._should_stop = False

    def stop(self) -> None:
        self._should_stop = True

    def run(self) -> None:
        if os.name != "nt":
            self.failed.emit("USB monitoring is available only on Windows")
            return
        import pythoncom
        import wmi
        pythoncom.CoInitialize()
        try:
            watcher = wmi.WMI().watch_for(wmi_class="Win32_VolumeChangeEvent")
            while not self._should_stop:
                try:
                    event = watcher(timeout_ms=1000)
                    kind = int(event.EventType)
                    if kind in (2, 3):
                        self.changed.emit(kind == 3)
                except wmi.x_wmi_timed_out:
                    continue
        except Exception as exc:
            LOG.exception("WMI event subscription failed")
            self.failed.emit(f"Windows volume-event subscription failed: {exc}")
        finally:
            pythoncom.CoUninitialize()
