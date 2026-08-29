"""
启动窗口

进入主界面后直接显示两个选项：
- 导入预设：选择 Celestial Evolution Simulation 的预设，
  仅输入"模拟时长 / 模拟时间步长 / 播放速度"后开始科学模拟；
- 新设置：先输入"星体数"，再逐个输入每个天体的位置、大小、质量等
  （输入方法同 Celestial Evolution Simulation），最后输入
  "模拟时长 / 模拟时间步长 / 播放速度"后开始科学模拟。

模拟期间不渲染，仅显示"模拟进度"；完成后按 60 FPS 回放记录的渲染帧。
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame,
)
from PyQt6.QtCore import Qt

from physics.scene_manager import SceneManager
from physics.mode import Mode
from scientific.precision import load_scene_preserving_precision
from scientific.simulator import (
    SimulationConfig,
    build_state_from_entries,
    build_state_from_scene,
)
from .setup_dialogs import PresetSetupDialog, NewSetupDialog
from .simulation_progress_dialog import SimulationProgressDialog
from .playback_window import PlaybackWindow
from .styles import apply_button_style


class StartupWindow(QMainWindow):
    """天体科学模拟器 - 主界面"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Celestial Evolution Scientific Simulation · 天体科学模拟器")
        self.setMinimumSize(720, 480)
        self.scene_manager = SceneManager()
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)

        # 标题
        title = QLabel("天体科学模拟器")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #E5E7EB;")
        layout.addWidget(title)

        subtitle = QLabel(
            "按时间步长直接进行离线 N 体模拟（无需渲染），显示模拟进度，"
            "完成后按 60 帧/秒回放渲染帧。\n"
            "支持超过 20 位有效数字的高精度计算（输入精度较小时使用常规 16 位精度）。"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        layout.addWidget(subtitle)

        layout.addSpacing(24)

        # 两个选项模块
        options = QHBoxLayout()
        options.setSpacing(24)

        preset_card = self._make_card(
            "导入预设",
            "使用 Celestial Evolution Simulation 的预设天体系统，"
            "仅需输入模拟时长、模拟时间步长、播放速度。",
            "选择预设并开始",
            self._on_import_preset,
        )
        options.addWidget(preset_card, 1)

        new_card = self._make_card(
            "新设置",
            "先输入星体数，再逐个输入每个天体的位置、大小、质量、速度等"
            "（输入方法同 Celestial Evolution Simulation），"
            "最后输入模拟时长、模拟时间步长、播放速度。",
            "开始新设置",
            self._on_new_setup,
        )
        options.addWidget(new_card, 1)

        layout.addLayout(options)
        layout.addStretch()

        defaults = QLabel(
            "默认参数：模拟时间步长 0.0001 TU，模拟时长 60 TU，播放速度 1 TU/s。"
        )
        defaults.setAlignment(Qt.AlignmentFlag.AlignCenter)
        defaults.setStyleSheet("color: #6B7280; font-size: 12px;")
        layout.addWidget(defaults)

    def _make_card(self, title, description, button_text, handler):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(
            "QFrame { background-color: #141824; border: 1px solid #2D3348;"
            " border-radius: 12px; }"
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size: 20px; font-weight: bold; color: #6366F1;")
        v.addWidget(t)

        d = QLabel(description)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setWordWrap(True)
        d.setStyleSheet("color: #9CA3AF; font-size: 13px;")
        v.addWidget(d)

        btn = QPushButton(button_text)
        apply_button_style(btn, 'primary')
        btn.setMinimumHeight(44)
        btn.clicked.connect(handler)
        v.addWidget(btn)

        return card

    # ---- 流程 ----
    def _on_import_preset(self):
        scenes = self.scene_manager.scan_scenes()
        if not scenes:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "没有预设", "scenes/ 目录下未找到任何预设文件。")
            return
        dlg = PresetSetupDialog(scenes, self)
        if dlg.exec() != PresetSetupDialog.DialogCode.Accepted:
            return
        data = dlg.result_data()

        try:
            scene = load_scene_preserving_precision(data['scene_path'])
            initial = build_state_from_scene(scene)
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "预设加载失败", f"{exc}")
            return

        config = SimulationConfig(
            duration=data['duration'],
            dt=data['dt'],
            playback_speed=data['playback_speed'],
            requested_digits=data['requested_digits'],
        )
        meta = {
            'scene_name': data.get('scene_name', ''),
            'unit_mode': '预设',
        }
        self._run_simulation(initial, config, meta)

    def _on_new_setup(self):
        dlg = NewSetupDialog(self)
        if dlg.exec() != NewSetupDialog.DialogCode.Accepted:
            return
        data = dlg.result_data()

        bodies = data['bodies']
        entries = data['entries']
        initial = build_state_from_entries(bodies, entries)
        config = SimulationConfig(
            duration=data['duration'],
            dt=data['dt'],
            playback_speed=data['playback_speed'],
            requested_digits=data['requested_digits'],
        )
        meta = {
            'scene_name': '',
            'unit_mode': data.get('unit_mode', '模拟'),
        }
        self._run_simulation(initial, config, meta)

    def _run_simulation(self, initial, config, meta: dict):
        """显示模拟进度；完成后打开回放窗口。"""
        dlg = SimulationProgressDialog(initial, config, self)
        dlg.exec()

        if dlg.error():
            return
        result = dlg.result()
        if result is None:
            return  # 已取消

        self.playback_window = PlaybackWindow(result, meta)
        self.playback_window.show()

