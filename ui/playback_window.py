"""
回放窗口

科学模拟完成后，按 60 FPS 回放已记录的渲染帧：
- 中央：PlaybackWidget（天体运动 + 轨迹）
- 底部：播放控制（播放/暂停、重播、帧滑杆、时间显示）
- 右侧：天体列表 + 检查器（10 Hz 刷新，展示当前帧每个天体的状态）
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QGroupBox, QFormLayout,
)
from PyQt6.QtCore import Qt, QTimer

from physics import Body, Mode, UnitSystem
from scientific.simulator import SimulationResult
from .playback_widget import PlaybackWidget
from .body_list_widget import BodyListWidget
from .inspector_widget import InspectorWidget

PLAYBACK_FPS = 60


class _FrameEngine:
    """为 BodyListWidget / InspectorWidget 提供当前帧状态（只读适配器）。"""

    def __init__(self):
        self.bodies = []
        self.simulation_time = 0.0

    def update_frame(self, result: SimulationResult, index: int):
        names = result.frame_names[index]
        colors = result.frame_colors[index]
        pos = result.frame_positions[index]
        vel = result.frame_velocities[index]
        mass = result.frame_masses[index]
        radii = result.frame_radii[index]
        bodies = []
        for i in range(len(pos)):
            c = colors[i] if i < len(colors) else (1.0, 1.0, 1.0)
            bodies.append(Body(
                name=names[i] if i < len(names) else f"Body {i+1}",
                mass=float(mass[i]),
                physical_radius=float(radii[i]),
                position=(float(pos[i][0]), float(pos[i][1])),
                velocity=(float(vel[i][0]), float(vel[i][1])),
                color=(float(c[0]), float(c[1]), float(c[2])),
            ))
        self.bodies = bodies
        self.simulation_time = result.frame_times[index]


class PlaybackWindow(QMainWindow):
    """渲染帧回放主窗口"""

    def __init__(self, result: SimulationResult, meta: dict = None, parent=None):
        super().__init__(parent)
        self._result = result
        self._meta = meta or {}
        self._playing = True
        self._frame_index = 0

        self.setWindowTitle("科学模拟回放")
        self.setMinimumSize(1000, 700)

        self.frame_engine = _FrameEngine()
        self.frame_engine.update_frame(result, 0)

        self._setup_ui()
        self._start_timer()

    # ---- UI ----
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # 中央回放 + 右侧信息
        top = QHBoxLayout()
        self.playback_widget = PlaybackWidget(self._result)
        top.addWidget(self.playback_widget, 3)

        side = QWidget()
        side.setFixedWidth(320)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(4, 4, 4, 4)

        self.info_group = QGroupBox("模拟信息")
        info_form = QFormLayout(self.info_group)
        self.summary_labels = {}
        items = [
            ('source', '来源'),
            ('duration', '模拟时长'),
            ('dt', '时间步长'),
            ('speed', '播放速度'),
            ('precision', '计算精度'),
            ('steps', '总步数'),
            ('wall', '计算耗时'),
            ('frames', '渲染帧数'),
        ]
        for key, label in items:
            lab = QLabel('-')
            lab.setWordWrap(True)
            self.summary_labels[key] = lab
            info_form.addRow(label + ':', lab)
        side_layout.addWidget(self.info_group)

        self.body_list = BodyListWidget(
            self.frame_engine, Mode.SIMULATION, UnitSystem(), None
        )
        side_layout.addWidget(self.body_list, 2)

        self.inspector = InspectorWidget(
            self.frame_engine, Mode.SIMULATION, UnitSystem(), None
        )
        side_layout.addWidget(self.inspector, 3)

        self.body_list.body_selected.connect(self.inspector.select_body)
        top.addWidget(side, 1)
        root.addLayout(top, 1)

        # 控制栏
        ctrl = QHBoxLayout()
        self.play_btn = QPushButton("⏸ 暂停")
        self.play_btn.setCheckable(True)
        self.play_btn.setChecked(True)
        self.play_btn.clicked.connect(self._on_toggle_play)
        ctrl.addWidget(self.play_btn)

        self.restart_btn = QPushButton("⏮ 重播")
        self.restart_btn.clicked.connect(self._on_restart)
        ctrl.addWidget(self.restart_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self._result.frame_count - 1)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._on_slider)
        ctrl.addWidget(self.slider, 1)

        self.frame_label = QLabel("帧 1/1")
        self.frame_label.setFixedWidth(120)
        ctrl.addWidget(self.frame_label)

        self.time_label = QLabel("t = 0.000000")
        self.time_label.setFixedWidth(140)
        ctrl.addWidget(self.time_label)

        root.addLayout(ctrl)

        # 更新信息面板
        self._update_info()

    def _update_info(self):
        r = self._result
        c = r.config
        self.summary_labels['source'].setText(
            self._meta.get('scene_name', '') or '新设置'
        )
        self.summary_labels['duration'].setText(f"{c.duration:g} TU")
        self.summary_labels['dt'].setText(f"{c.dt:g} TU")
        self.summary_labels['speed'].setText(
            f"{c.playback_speed:g} TU/s（60 帧/秒）"
        )
        if r.precision_mode == 'float64':
            prec = "float64（16 位有效数字）"
        else:
            prec = f"Decimal 高精度（{r.precision_digits} 位有效数字）"
        self.summary_labels['precision'].setText(prec)
        self.summary_labels['steps'].setText(f"{r.total_steps:,}")
        self.summary_labels['wall'].setText(f"{r.elapsed_seconds:.2f} s")
        self.summary_labels['frames'].setText(f"{r.frame_count:,}")

    # ---- 定时器 ----
    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / PLAYBACK_FPS))
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _on_tick(self):
        if not self._playing:
            return
        if self._frame_index >= self._result.frame_count - 1:
            self._playing = False
            self.play_btn.setChecked(False)
            self.play_btn.setText("▶ 播放")
            self.slider.blockSignals(True)
            self.slider.setValue(self._result.frame_count - 1)
            self.slider.blockSignals(False)
            self._set_frame(self._result.frame_count - 1)
            return
        self._set_frame(self._frame_index + 1)
        self.slider.blockSignals(True)
        self.slider.setValue(self._frame_index)
        self.slider.blockSignals(False)

    # ---- 控制 ----
    def _on_toggle_play(self):
        self._playing = self.play_btn.isChecked()
        self.play_btn.setText("⏸ 暂停" if self._playing else "▶ 播放")

    def _on_restart(self):
        self._playing = True
        self.play_btn.setChecked(True)
        self.play_btn.setText("⏸ 暂停")
        self._set_frame(0)
        self.slider.blockSignals(True)
        self.slider.setValue(0)
        self.slider.blockSignals(False)

    def _on_slider(self, value: int):
        self._set_frame(value)

    def _set_frame(self, index: int):
        index = max(0, min(index, self._result.frame_count - 1))
        self._frame_index = index
        self.playback_widget.set_frame(index)
        self.frame_engine.update_frame(self._result, index)
        self.frame_label.setText(f"帧 {index + 1}/{self._result.frame_count}")
        t = self._result.frame_times[index]
        self.time_label.setText(f"t = {t:.6f} TU")
        # 10 Hz 刷新天体列表/检查器（每 6 帧刷新一次）
        if index % 6 == 0:
            self.body_list.refresh()
            self.inspector.refresh()
