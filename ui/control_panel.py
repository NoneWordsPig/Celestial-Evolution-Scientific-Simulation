"""
Control Panel

控制面板，包含播放控制和时间缩放
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QComboBox, QLabel, QGroupBox
)
from PyQt6.QtCore import pyqtSignal

from physics import PhysicsEngine


class ControlPanel(QWidget):
    """
    控制面板组件
    
    包含：
    - 播放/暂停/单步控制
    - 时间缩放选择
    """
    
    # 信号
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    step_requested = pyqtSignal()
    time_scale_changed = pyqtSignal(float)
    
    def __init__(self, engine: PhysicsEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 播放控制组
        play_group = QGroupBox("播放控制")
        play_layout = QHBoxLayout()
        
        # 播放/暂停按钮
        self.play_pause_btn = QPushButton("⏸ 暂停")
        self.play_pause_btn.setCheckable(True)
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        play_layout.addWidget(self.play_pause_btn)
        
        # 单步按钮
        self.step_btn = QPushButton("⏭ 单步")
        self.step_btn.clicked.connect(self._on_step_clicked)
        play_layout.addWidget(self.step_btn)
        
        play_group.setLayout(play_layout)
        layout.addWidget(play_group)
        
        # 时间缩放组
        scale_group = QGroupBox("时间缩放")
        scale_layout = QHBoxLayout()
        
        scale_layout.addWidget(QLabel("速度:"))
        
        self.time_scale_combo = QComboBox()
        time_scales = [
            ("0.1×", 0.1),
            ("0.5×", 0.5),
            ("1×", 1.0),
            ("2×", 2.0),
            ("5×", 5.0),
            ("10×", 10.0),
            ("100×", 100.0),
        ]
        for label, value in time_scales:
            self.time_scale_combo.addItem(label, value)
        
        # 默认选择 1×
        self.time_scale_combo.setCurrentIndex(2)
        self.time_scale_combo.currentIndexChanged.connect(self._on_time_scale_changed)
        scale_layout.addWidget(self.time_scale_combo)
        
        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)
        
        # 占位符
        layout.addStretch()
    
    def _on_play_pause_clicked(self):
        """播放/暂停按钮点击"""
        if self.play_pause_btn.isChecked():
            self.play_pause_btn.setText("▶ 播放")
            self.pause_requested.emit()
        else:
            self.play_pause_btn.setText("⏸ 暂停")
            self.play_requested.emit()
    
    def _on_step_clicked(self):
        """单步按钮点击"""
        self.step_requested.emit()
    
    def _on_time_scale_changed(self):
        """时间缩放变化"""
        value = self.time_scale_combo.currentData()
        self.engine.time_scale = value
        self.time_scale_changed.emit(value)
    
    def set_paused(self, paused: bool):
        """设置暂停状态"""
        self.play_pause_btn.setChecked(paused)
        if paused:
            self.play_pause_btn.setText("▶ 播放")
        else:
            self.play_pause_btn.setText("⏸ 暂停")
