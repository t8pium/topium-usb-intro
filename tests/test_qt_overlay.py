"""Optional Qt offscreen playback integration test; run on Windows CI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
pytest.importorskip("PySide6", reason="PySide6 is not installed in this environment")
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from topium_usb_intro.models import Profile
from topium_usb_intro.playback import Overlay


def test_one_visible_cycle_completes_once_even_if_gif_is_infinite():
    app = QApplication.instance() or QApplication([])
    overlay = Overlay()
    profile = Profile(name="Demo", disk_pnp_id="SIM", volume_serial="123", volume_guid="",
                      fade_ms=0, max_duration_ms=3500)
    count = []
    loop = QEventLoop()
    overlay.completed.connect(lambda: (count.append(True), loop.quit()))
    QTimer.singleShot(4500, loop.quit)
    overlay.play(profile)
    loop.exec()
    assert count == [True]
    assert not overlay.isVisible()
    overlay.close()
