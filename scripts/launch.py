"""PyInstaller-safe entrypoint for packaged executable."""
from topium_usb_intro.__main__ import main
if __name__ == "__main__":
    raise SystemExit(main())
