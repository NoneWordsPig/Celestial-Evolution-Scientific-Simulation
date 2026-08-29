"""
模拟进度对话框

后台线程执行离线模拟（不渲染），对话框实时显示"模拟进度"：
- 进度条 + 百分比
- 已计算步数 / 总步数
- 已用时间 / 预计剩余时间
- 支持取消
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt

from scientific.worker import SimulationWorker


class SimulationProgressDialog(QDialog):
    """显示科学模拟进度的模态对话框"""

    def __init__(self, initial, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("科学模拟进度")
        self.setMinimumWidth(520)
        self._result = None
        self._error = None

        layout = QVBoxLayout(self)

        title = QLabel("正在按时间步长进行模拟（无需渲染）…")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.info_label = QLabel("准备中…")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #9ca3af;")
        layout.addWidget(self.info_label)

        btns = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btns.addStretch()
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

        # 后台线程
        self.worker = SimulationWorker(initial, config, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    # ---- 信号处理 ----
    def _on_progress(self, percent: int, text: str):
        self.progress_bar.setValue(percent)
        self.info_label.setText(text)

    def _on_finished(self, result):
        self._result = result
        self.accept()

    def _on_failed(self, message: str):
        self._error = message
        self.accept()

    def _on_cancel(self):
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("正在取消…")
        self.info_label.setText("正在取消…")
        self.worker.cancel()
        self.worker.finished.connect(self._on_worker_finished_after_cancel)

    def _on_worker_finished_after_cancel(self):
        # 取消后：没有结果也没有错误时，关闭对话框（表示用户已取消）
        if self._result is None and self._error is None:
            self.reject()

    def result(self):
        """返回 SimulationResult；取消/失败返回 None。"""
        return self._result

    def error(self) -> str:
        return self._error

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        super().closeEvent(event)

    # 成功后弹窗由调用方处理
    def done(self, r):
        super().done(r)
        if self._error is not None:
            QMessageBox.critical(self, "模拟失败", self._error)

