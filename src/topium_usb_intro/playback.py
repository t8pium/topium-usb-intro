"""Qt frameless overlay driven by our own one-cycle GIF frame timer."""
from __future__ import annotations
import logging
from pathlib import Path
from importlib.resources import files
from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication
from .gif_frames import GifFrame, load_one_cycle
from .models import Profile

LOG = logging.getLogger(__name__)


def bundled_gif() -> Path:
    return Path(str(files("topium_usb_intro").joinpath("assets", "sample_intro.gif")))


class Overlay(QWidget):
    completed = Signal()

    def __init__(self) -> None:
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                 Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self._frames: list[GifFrame] = []
        self._index = 0
        self._running = False
        self._elapsed = 0
        self._generation = 0
        self._config: Profile | None = None
        self._fade: QPropertyAnimation | None = None

    def play(self, config: Profile) -> None:
        self.finish(emit=False)
        self._config = config
        self._generation += 1
        generation = self._generation
        path = Path(config.gif_path) if config.gif_path else bundled_gif()
        try:
            self._frames = load_one_cycle(path)
        except (ValueError, OSError) as exc:
            LOG.warning("Selected GIF not usable; trying sample animation: %s", type(exc).__name__)
            try:
                self._frames = load_one_cycle(bundled_gif())
            except (ValueError, OSError):
                QTimer.singleShot(0, self.completed.emit)
                return
        self._index = 0
        self._elapsed = 0
        self._running = True
        self.setWindowOpacity(1.0)
        width = min(config.size, self._frames[0].width * 4)
        height = max(1, round(width * self._frames[0].height / self._frames[0].width))
        self.resize(width, height)
        screen = QApplication.screenAt(self.cursor().pos()) or QApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            if config.position == "center":
                x = rect.x() + (rect.width() - width) // 2
                y = rect.y() + (rect.height() - height) // 2
            else:
                x = rect.right() - width - 32
                y = rect.bottom() - height - 32
            self.move(x, y)
        self.show()
        self._render_next(generation)

    def _render_next(self, generation: int) -> None:
        if not self._running or generation != self._generation:
            return
        if self._index >= len(self._frames):
            self._begin_fade(generation)
            return
        if self._config and self._elapsed >= self._config.max_duration_ms:
            self._begin_fade(generation)
            return
        frame = self._frames[self._index]
        img = QImage(frame.rgba, frame.width, frame.height, frame.width * 4,
                     QImage.Format.Format_RGBA8888).copy()
        self.label.setPixmap(QPixmap.fromImage(img).scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        self._index += 1
        budget = max(0, self._config.max_duration_ms - self._elapsed) if self._config else 0
        delay = min(frame.duration_ms, budget)
        self._elapsed += delay
        QTimer.singleShot(delay, lambda: self._render_next(generation))

    def _begin_fade(self, generation: int) -> None:
        if generation != self._generation:
            return
        duration = self._config.fade_ms if self._config else 0
        if duration == 0:
            self.finish()
            return
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(duration)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._fade.finished.connect(self.finish)
        self._fade.start()
        # Failsafe if a particular compositor does not advance opacity animation.
        QTimer.singleShot(duration + 200,
                          lambda: self.finish() if self._running and
                          generation == self._generation else None)

    def finish(self, emit: bool = True) -> None:
        was_running = self._running
        self._running = False
        self._generation += 1
        if self._fade:
            self._fade.stop()
            self._fade = None
        self.hide()
        self._frames = []
        if emit and was_running:
            self.completed.emit()
