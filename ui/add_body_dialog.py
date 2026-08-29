"""
Add Body Dialog

添加天体对话框
支持两种速度输入模式：笛卡尔坐标（vx, vy）和极坐标（speed, angle）
"""

import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QColorDialog, QLabel, QGroupBox,
    QRadioButton, QButtonGroup, QStackedWidget, QWidget, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from physics import Body, Mode, UnitSystem, UnitConverter
from physics.unit_system import UnitSystem as ScientificUnitSystem
from .scientific_number_input import ScientificNumberInput


class AddBodyDialog(QDialog):
    """
    添加天体对话框
    
    根据当前 Mode 显示不同的单位
    支持两种速度输入模式：
    - 笛卡尔坐标模式：vx, vy
    - 极坐标模式：speed, angle
    """
    
    def __init__(
        self,
        mode: Mode = Mode.SIMULATION,
        unit_system: UnitSystem = None,
        converter: UnitConverter = None,
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.unit_system = unit_system or UnitSystem()
        self.converter = converter
        # 独立科学归一化 UnitSystem：科学模式现实单位 -> normalized simulation units
        self.scientific_units = ScientificUnitSystem()
        
        self._selected_color = (0.3, 0.5, 1.0)  # 默认蓝色
        self._velocity_mode = 'polar'  # 默认极坐标模式
        
        self.setWindowTitle("添加天体")
        self.setMinimumWidth(350)
        
        self._setup_ui()

    def _unit_row(self, widget, units, default_unit):
        """
        为数值输入附加单位选择器（仅科学模式使用）。

        Returns:
            (容器 QWidget, QComboBox)
        """
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        combo = QComboBox()
        combo.addItems(units)
        combo.setCurrentText(default_unit)

        row_layout.addWidget(widget, 1)
        row_layout.addWidget(combo)
        return row, combo
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        # 名称
        self.name_edit = QLineEdit("Planet")
        basic_layout.addRow("名称:", self.name_edit)
        
        # 质量
        self.mass_spin = ScientificNumberInput(
            value=1.0, min_value=1e-30, max_value=1e38,
            suffix=" MU" if self.mode == Mode.SIMULATION else ""
        )

        if self.mode == Mode.SCIENTIFIC:
            mass_row, self.mass_unit_combo = self._unit_row(
                self.mass_spin, ["kg", "M_sun"], "M_sun"
            )
            basic_layout.addRow("质量:", mass_row)
        else:
            basic_layout.addRow("质量:", self.mass_spin)
        
        # 半径
        self.radius_spin = ScientificNumberInput(
            value=1e-4, min_value=1e-30, max_value=1e12,
            suffix=" DU" if self.mode == Mode.SIMULATION else ""
        )

        if self.mode == Mode.SCIENTIFIC:
            radius_row, self.radius_unit_combo = self._unit_row(
                self.radius_spin, ["m", "km", "AU"], "km"
            )
            basic_layout.addRow("半径:", radius_row)
        else:
            basic_layout.addRow("半径:", self.radius_spin)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 位置组
        pos_group = QGroupBox("位置")
        pos_layout = QFormLayout()
        
        self.pos_x_spin = ScientificNumberInput(
            value=0.0, min_value=-1e18, max_value=1e18,
            suffix=" DU" if self.mode == Mode.SIMULATION else ""
        )
        self.pos_y_spin = ScientificNumberInput(
            value=0.0, min_value=-1e18, max_value=1e18,
            suffix=" DU" if self.mode == Mode.SIMULATION else ""
        )

        if self.mode == Mode.SCIENTIFIC:
            pos_x_row, self.pos_x_unit_combo = self._unit_row(
                self.pos_x_spin, ["m", "km", "AU"], "AU"
            )
            pos_y_row, self.pos_y_unit_combo = self._unit_row(
                self.pos_y_spin, ["m", "km", "AU"], "AU"
            )
            pos_layout.addRow("X:", pos_x_row)
            pos_layout.addRow("Y:", pos_y_row)
        else:
            pos_layout.addRow("X:", self.pos_x_spin)
            pos_layout.addRow("Y:", self.pos_y_spin)
        
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # 速度组
        vel_group = QGroupBox("速度")
        vel_layout = QVBoxLayout()
        
        # 速度输入模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("输入模式:")
        mode_layout.addWidget(mode_label)
        
        self.cartesian_radio = QRadioButton("X/Y")
        self.polar_radio = QRadioButton("V/θ")
        self.polar_radio.setChecked(True)  # 默认极坐标
        
        self.velocity_mode_group = QButtonGroup()
        self.velocity_mode_group.addButton(self.cartesian_radio, 0)
        self.velocity_mode_group.addButton(self.polar_radio, 1)
        
        mode_layout.addWidget(self.cartesian_radio)
        mode_layout.addWidget(self.polar_radio)
        mode_layout.addStretch()
        
        # 连接信号：模式切换时更新输入区域
        self.velocity_mode_group.buttonClicked.connect(self._on_velocity_mode_changed)
        
        vel_layout.addLayout(mode_layout)
        
        # 速度输入堆叠组件
        self.vel_stack = QStackedWidget()
        
        # 笛卡尔模式页面
        cartesian_page = QWidget()
        cartesian_layout = QFormLayout()
        
        self.vx_spin = ScientificNumberInput(
            value=0.0, min_value=-1e12, max_value=1e12,
            suffix=" DU/TU" if self.mode == Mode.SIMULATION else ""
        )
        self.vy_spin = ScientificNumberInput(
            value=0.0, min_value=-1e12, max_value=1e12,
            suffix=" DU/TU" if self.mode == Mode.SIMULATION else ""
        )

        if self.mode == Mode.SCIENTIFIC:
            vx_row, self.vx_unit_combo = self._unit_row(
                self.vx_spin, ["m/s", "km/s", "AU/T0"], "km/s"
            )
            vy_row, self.vy_unit_combo = self._unit_row(
                self.vy_spin, ["m/s", "km/s", "AU/T0"], "km/s"
            )
            cartesian_layout.addRow("vx:", vx_row)
            cartesian_layout.addRow("vy:", vy_row)
        else:
            cartesian_layout.addRow("vx:", self.vx_spin)
            cartesian_layout.addRow("vy:", self.vy_spin)
        
        cartesian_page.setLayout(cartesian_layout)
        self.vel_stack.addWidget(cartesian_page)
        
        # 极坐标模式页面
        polar_page = QWidget()
        polar_layout = QFormLayout()
        
        self.speed_spin = ScientificNumberInput(
            value=0.0, min_value=0.0, max_value=1e12,
            suffix=" DU/TU" if self.mode == Mode.SIMULATION else ""
        )
        self.direction_spin = ScientificNumberInput(
            value=0.0, min_value=-360.0, max_value=360.0, suffix="°"
        )

        if self.mode == Mode.SCIENTIFIC:
            speed_row, self.speed_unit_combo = self._unit_row(
                self.speed_spin, ["m/s", "km/s", "AU/T0"], "km/s"
            )
            polar_layout.addRow("速率:", speed_row)
        else:
            polar_layout.addRow("速率:", self.speed_spin)
        polar_layout.addRow("角度:", self.direction_spin)
        
        polar_page.setLayout(polar_layout)
        self.vel_stack.addWidget(polar_page)
        
        # 默认显示极坐标页面（与 polar_radio 选中状态一致）
        self.vel_stack.setCurrentIndex(1)
        
        vel_layout.addWidget(self.vel_stack)
        
        vel_group.setLayout(vel_layout)
        layout.addWidget(vel_group)
        
        # 连接信号
        self.cartesian_radio.toggled.connect(self._on_velocity_mode_changed)
        self.polar_radio.toggled.connect(self._on_velocity_mode_changed)
        
        # 颜色
        color_group = QGroupBox("颜色")
        color_layout = QHBoxLayout()
        
        self.color_label = QLabel("████")
        self._update_color_display()
        color_layout.addWidget(self.color_label)
        
        self.color_btn = QPushButton("选择颜色...")
        self.color_btn.clicked.connect(self._on_color_clicked)
        color_layout.addWidget(self.color_btn)
        
        color_layout.addStretch()
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _on_velocity_mode_changed(self):
        """速度输入模式切换"""
        if self.cartesian_radio.isChecked():
            # 切换到笛卡尔模式
            # 从极坐标转换到笛卡尔
            speed = self.speed_spin.value()
            angle_rad = np.radians(self.direction_spin.value())
            vx = speed * np.cos(angle_rad)
            vy = speed * np.sin(angle_rad)
            
            self.vx_spin.setValue(vx)
            self.vy_spin.setValue(vy)
            
            self.vel_stack.setCurrentIndex(0)
            self._velocity_mode = 'cartesian'
        else:
            # 切换到极坐标模式
            # 从笛卡尔转换到极坐标
            vx = self.vx_spin.value()
            vy = self.vy_spin.value()
            
            speed = np.sqrt(vx**2 + vy**2)
            angle = np.degrees(np.arctan2(vy, vx))
            
            self.speed_spin.setValue(speed)
            self.direction_spin.setValue(angle)
            
            self.vel_stack.setCurrentIndex(1)
            self._velocity_mode = 'polar'
    
    def _on_color_clicked(self):
        """选择颜色"""
        color = QColorDialog.getColor(
            QColor(
                int(self._selected_color[0] * 255),
                int(self._selected_color[1] * 255),
                int(self._selected_color[2] * 255)
            ),
            self
        )
        if color.isValid():
            self._selected_color = (
                color.red() / 255.0,
                color.green() / 255.0,
                color.blue() / 255.0
            )
            self._update_color_display()
    
    def _update_color_display(self):
        """更新颜色显示"""
        r, g, b = self._selected_color
        self.color_label.setStyleSheet(
            f"background-color: rgb({int(r*255)}, {int(g*255)}, {int(b*255)}); "
            f"padding: 5px; border: 1px solid gray;"
        )
    
    def get_body(self) -> Body:
        """
        获取创建的天体

        科学模式：UI 现实单位 -> UnitSystem -> normalized simulation units
        模拟模式：直接使用 normalized simulation units
        Physics Engine 只接收 normalized values（G = 1）。
        """
        if self.mode == Mode.SIMULATION:
            # 模拟模式：直接使用 normalized simulation units
            mass = self.mass_spin.value()
            radius = self.radius_spin.value()
            pos_x = self.pos_x_spin.value()
            pos_y = self.pos_y_spin.value()
        else:
            # 科学模式：UI 现实单位 -> UnitSystem -> normalized simulation units
            mass = self.scientific_units.to_simulation(
                self.mass_spin.value(), self.mass_unit_combo.currentText()
            )
            radius = self.scientific_units.to_simulation(
                self.radius_spin.value(), self.radius_unit_combo.currentText()
            )
            pos_x = self.scientific_units.to_simulation(
                self.pos_x_spin.value(), self.pos_x_unit_combo.currentText()
            )
            pos_y = self.scientific_units.to_simulation(
                self.pos_y_spin.value(), self.pos_y_unit_combo.currentText()
            )
        
        # 获取速度向量
        if self._velocity_mode == 'cartesian':
            if self.mode == Mode.SIMULATION:
                vx = self.vx_spin.value()
                vy = self.vy_spin.value()
            else:
                vx = self.scientific_units.to_simulation(
                    self.vx_spin.value(), self.vx_unit_combo.currentText()
                )
                vy = self.scientific_units.to_simulation(
                    self.vy_spin.value(), self.vy_unit_combo.currentText()
                )
        else:
            if self.mode == Mode.SIMULATION:
                speed = self.speed_spin.value()
            else:
                speed = self.scientific_units.to_simulation(
                    self.speed_spin.value(), self.speed_unit_combo.currentText()
                )
            
            direction_rad = np.radians(self.direction_spin.value())
            vx = speed * np.cos(direction_rad)
            vy = speed * np.sin(direction_rad)
        
        return Body(
            name=self.name_edit.text(),
            mass=mass,
            physical_radius=radius,
            position=(pos_x, pos_y),
            velocity=(vx, vy),
            color=self._selected_color
        )

    def get_body_raw(self) -> dict:
        """
        获取高精度原始输入（保留输入框中的完整文本与单位选择）。

        科学模拟使用该方法读取原始文本，以便在输入精度超过 float64
        （约 16 位）时启用高精度 Decimal 计算；数值本身不做任何舍入。
        """
        is_sci = self.mode == Mode.SCIENTIFIC
        data = {
            'name': self.name_edit.text(),
            'mass': self.mass_spin.raw_text(),
            'radius': self.radius_spin.raw_text(),
            'pos_x': self.pos_x_spin.raw_text(),
            'pos_y': self.pos_y_spin.raw_text(),
            'color': self._selected_color,
            'is_scientific': is_sci,
            'velocity': {},
        }
        if is_sci:
            data['mass_unit'] = self.mass_unit_combo.currentText()
            data['radius_unit'] = self.radius_unit_combo.currentText()
            data['pos_x_unit'] = self.pos_x_unit_combo.currentText()
            data['pos_y_unit'] = self.pos_y_unit_combo.currentText()

        if self._velocity_mode == 'cartesian':
            data['velocity']['mode'] = 'cartesian'
            data['velocity']['vx'] = self.vx_spin.raw_text()
            data['velocity']['vy'] = self.vy_spin.raw_text()
            if is_sci:
                data['velocity']['vx_unit'] = self.vx_unit_combo.currentText()
                data['velocity']['vy_unit'] = self.vy_unit_combo.currentText()
        else:
            data['velocity']['mode'] = 'polar'
            data['velocity']['speed'] = self.speed_spin.raw_text()
            data['velocity']['angle'] = self.direction_spin.raw_text()
            if is_sci:
                data['velocity']['speed_unit'] = self.speed_unit_combo.currentText()

        return data

    def set_body(self, body: Body) -> None:
        """
        用已有天体填充输入框（用于编辑）。

        速度输入统一切换到笛卡尔 X/Y 模式，避免极坐标往返舍入。
        """
        self.name_edit.setText(body.name)
        if self.mode == Mode.SIMULATION:
            self.mass_spin.setValue(float(body.mass))
            self.radius_spin.setValue(float(body.physical_radius))
            self.pos_x_spin.setValue(float(body.position[0]))
            self.pos_y_spin.setValue(float(body.position[1]))
        else:
            self.mass_spin.setValue(float(self.scientific_units.from_simulation(
                body.mass, self.mass_unit_combo.currentText())))
            self.radius_spin.setValue(float(self.scientific_units.from_simulation(
                body.physical_radius, self.radius_unit_combo.currentText())))
            self.pos_x_spin.setValue(float(self.scientific_units.from_simulation(
                body.position[0], self.pos_x_unit_combo.currentText())))
            self.pos_y_spin.setValue(float(self.scientific_units.from_simulation(
                body.position[1], self.pos_y_unit_combo.currentText())))

        if not self.cartesian_radio.isChecked():
            self.cartesian_radio.setChecked(True)
        self.vx_spin.setValue(float(body.velocity[0]))
        self.vy_spin.setValue(float(body.velocity[1]))
        self.vel_stack.setCurrentIndex(0)
        self._velocity_mode = 'cartesian'
