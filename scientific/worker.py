"""
Qt 后台模拟线程

将耗时的离线模拟放到后台线程执行，通过信号向 UI 报告：
- progress(percent, text)   模拟进度
- finished_ok(result)       模拟完成（SimulationResult）
- failed(message)           模拟失败
"""

from PyQt6.QtCore import QThread, pyqtSignal

from .simulator import InitialState, SimulationConfig, run_simulation


class SimulationWorker(QThread):
    """后台科学模拟线程"""

    progress = pyqtSignal(int, str)
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, initial: InitialState, config: SimulationConfig, parent=None):
        super().__init__(parent)
        self._initial = initial
        self._config = config
        self._cancelled = False

    def cancel(self) -> None:
        """请求取消（线程会在下一个时间步检查）。"""
        self._cancelled = True

    def run(self) -> None:
        try:
            result = run_simulation(
                self._initial,
                self._config,
                progress=lambda p, t: self.progress.emit(p, t),
                cancel=lambda: self._cancelled,
            )
        except Exception as exc:  # noqa: BLE001 - 全部上报给 UI
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        if result is None:
            # 用户取消
            return
        self.finished_ok.emit(result)
