# Upstream references

- Microsoft: Win32_VolumeChangeEvent class (EventType 2 arrival, 3 removal): https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-volumechangeevent
- Microsoft: WM_DEVICECHANGE and device arrival: https://learn.microsoft.com/en-us/windows/win32/devio/wm-devicechange
- Qt for Python: QMovie docs (loopCount -1 means infinite; end signal cannot safely be used to terminate such playback): https://doc.qt.io/qtforpython-6/PySide6/QtGui/QMovie.html
- Windows Management Instrumentation (WMI) Python package: https://pypi.org/project/WMI/
- PyInstaller: https://pyinstaller.org/en/stable/

This app uses a Pillow-decoded, QTimer-driven finite frame sequence instead of relying on QMovie's `finished` signal for infinitely looping GIFs.
