# Build on Windows only. Produces a single executable that can copy itself to
# %LOCALAPPDATA% when the user clicks 'Enable automatic intro'.
$ErrorActionPreference = "Stop"
python -m pip install -e ".[build,test]"
python -m pytest -q
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TOPIUM-USB-INTRO --collect-data topium_usb_intro --collect-all wmi --hidden-import pythoncom --hidden-import win32com.client scripts/launch.py
Write-Host "Build candidate: dist\TOPIUM-USB-INTRO.exe"
Write-Host "Not hardware-verified until a physical Windows USB test succeeds."
