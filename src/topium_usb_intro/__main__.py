"""Windows event-triggered application: setup or brief per-insertion run."""
from __future__ import annotations

import argparse
import logging
import sys
from . import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="TOPIUM USB INTRO — no resident monitor")
    parser.add_argument("--settings", action="store_true", help="configure a connected drive")
    parser.add_argument("--on-connect", action="store_true", help="transient run invoked by Windows Task Scheduler")
    parser.add_argument("--event-device-id", default="", help="DeviceId from the Windows event that triggered this run")
    parser.add_argument("--task-admin", choices=("install", "remove"), help=argparse.SUPPRESS)
    parser.add_argument("--task-xml", default="", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    from .logging_setup import setup_logging
    setup_logging()
    if args.task_admin:
        from .event_task import elevated_action
        return elevated_action(args.task_admin, args.task_xml)
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])
    app.setApplicationName("TOPIUM USB INTRO")
    app.setOrganizationName("TOPIUM")
    app.setQuitOnLastWindowClosed(True)
    if args.on_connect:
        from .one_shot import OneShot
        controller = OneShot(app, args.event_device_id)
    else:
        from .configure import SetupWindow
        window = SetupWindow()
        window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
