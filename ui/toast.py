"""
轻量提示气泡（Toast）

有限时长显示，带出现/消失动画（透明度淡入淡出）。
仅作信息提示，不修改任何模拟设置。
"""

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class Toast(QLabel):
    """
    主窗口内的提示气泡

    show_message(text, duration_ms):
        淡入（200ms）-> 保持 duration_ms -> 淡出（300ms）-> finished 信号
    """

    finished = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toastLabel")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            "QLabel#toastLabel {"
            "  background-color: rgba(24, 24, 34, 225);"
            "  color: #ffffff;"
            "  border: 1px solid rgba(255, 255, 255, 90);"
            "  border-radius: 8px;"
            "  padding: 10px 18px;"
            "  font-size: 14px;"
            "}"
        )

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        self._fade_in = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self._on_fade_out_finished)

        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._start_fade_out)

        self._is_showing = False
        self.hide()

    @property
    def is_showing(self) -> bool:
        """气泡是否正在显示（含淡入/保持/淡出阶段）"""
        return self._is_showing

    def show_message(self, text: str, duration_ms: int = 5000) -> None:
        """显示提示：淡入 -> 保持 duration_ms -> 淡出"""
        self.setText(text)
        self._center_top()
        self._hold_timer.stop()
        self._fade_out.stop()
        self._opacity.setOpacity(0.0)
        self._is_showing = True
        self.show()
        self.raise_()
        self._fade_in.start()
        self._hold_timer.start(duration_ms)

    def _center_top(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        self.move(max(0, (parent.width() - self.width()) // 2), 16)

    def _start_fade_out(self) -> None:
        self._fade_in.stop()
        self._fade_out.start()

    def _on_fade_out_finished(self) -> None:
        self._is_showing = False
        self.hide()
        self.finished.emit()