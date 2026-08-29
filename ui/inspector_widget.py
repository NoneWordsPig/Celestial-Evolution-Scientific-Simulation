"""
Inspector Widget

右侧检查器，显示选中天体的详细信息
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout
from PyQt6.QtCore import Qt

from physics import PhysicsEngine, SimulationFormatter, ScientificFormatter, Mode, UnitSystem, UnitConverter


class InspectorWidget(QWidget):
    """
    检查器组件
    
    显示选中天体的详细信息
    """
    
    def __init__(
        self,
        engine: PhysicsEngine,
        mode: Mode = Mode.SIMULATION,
        unit_system: UnitSystem = None,
        converter: UnitConverter = None,
        parent=None
    ):
        super().__init__(parent)
        self.engine = engine
        self.mode = mode
        self.unit_system = unit_system or UnitSystem()
        self.converter = converter
        
        self._selected_index = -1
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("检查器")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 基本信息组
        self.basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        self.name_label = QLabel("-")
        self.mass_label = QLabel("-")
        self.radius_label = QLabel("-")
        
        basic_layout.addRow("名称:", self.name_label)
        basic_layout.addRow("质量:", self.mass_label)
        basic_layout.addRow("半径:", self.radius_label)
        
        self.basic_group.setLayout(basic_layout)
        layout.addWidget(self.basic_group)
        
        # 位置速度组
        self.motion_group = QGroupBox("运动状态")
        motion_layout = QFormLayout()
        
        self.position_label = QLabel("-")
        self.velocity_label = QLabel("-")
        self.speed_label = QLabel("-")
        self.direction_label = QLabel("-")
        
        motion_layout.addRow("位置:", self.position_label)
        motion_layout.addRow("速度:", self.velocity_label)
        motion_layout.addRow("速率:", self.speed_label)
        motion_layout.addRow("方向:", self.direction_label)
        
        self.motion_group.setLayout(motion_layout)
        layout.addWidget(self.motion_group)
        
        # 物理量组
        self.physics_group = QGroupBox("物理量")
        physics_layout = QFormLayout()
        
        self.ke_label = QLabel("-")
        self.momentum_label = QLabel("-")
        
        physics_layout.addRow("动能:", self.ke_label)
        physics_layout.addRow("动量:", self.momentum_label)
        
        self.physics_group.setLayout(physics_layout)
        layout.addWidget(self.physics_group)
        
        # 占位符
        layout.addStretch()
        
        # 初始状态
        self._show_no_selection()
    
    def select_body(self, index: int):
        """选中天体"""
        self._selected_index = index
        self.refresh()
    
    def refresh(self):
        """刷新显示"""
        if self._selected_index < 0 or self._selected_index >= len(self.engine.bodies):
            self._show_no_selection()
            return
        
        body = self.engine.bodies[self._selected_index]
        
        # 选择格式化器
        if self.mode == Mode.SIMULATION:
            formatter = SimulationFormatter(self.unit_system)
        else:
            formatter = ScientificFormatter(self.unit_system, self.converter)
        
        # 基本信息
        self.name_label.setText(body.name)
        self.mass_label.setText(formatter.format_mass(body.mass))
        self.radius_label.setText(formatter.format_distance(body.physical_radius))
        
        # 位置
        pos_str = formatter.format_position(body.position[0], body.position[1])
        self.position_label.setText(pos_str)
        
        # 速度
        vel_str = formatter.format_velocity_vector(body.velocity[0], body.velocity[1])
        self.velocity_label.setText(vel_str)
        
        # 速率
        import numpy as np
        speed = np.linalg.norm(body.velocity)
        self.speed_label.setText(formatter.format_velocity(speed))
        
        # 方向
        if speed > 1e-10:
            angle = np.degrees(np.arctan2(body.velocity[1], body.velocity[0]))
            if angle < 0:
                angle += 360
            self.direction_label.setText(f"{angle:.1f}°")
        else:
            self.direction_label.setText("-")
        
        # 动能
        ke = body.kinetic_energy()
        self.ke_label.setText(formatter.format_energy(ke))
        
        # 动量
        momentum = body.momentum()
        self.momentum_label.setText(formatter.format_momentum(momentum[0], momentum[1]))
    
    def set_mode(
        self,
        mode: Mode,
        unit_system: UnitSystem = None,
        converter: UnitConverter = None
    ):
        """设置模式"""
        self.mode = mode
        if unit_system:
            self.unit_system = unit_system
        if converter is not None:
            self.converter = converter
        self.refresh()
    
    def _show_no_selection(self):
        """显示未选中状态"""
        self.name_label.setText("-")
        self.mass_label.setText("-")
        self.radius_label.setText("-")
        self.position_label.setText("-")
        self.velocity_label.setText("-")
        self.speed_label.setText("-")
        self.direction_label.setText("-")
        self.ke_label.setText("-")
        self.momentum_label.setText("-")
