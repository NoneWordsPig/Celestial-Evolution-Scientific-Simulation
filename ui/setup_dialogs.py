"""
科学模拟设置对话框

包含：
- PresetSetupDialog：导入预设（选择预设 + 模拟时长/时间步长/播放速度）
- NewSetupDialog：新设置（星体数 + 逐个输入天体参数 + 三个模拟参数）
- SimulationParamsWidget：三个模拟参数 + 可选计算精度

"输入方法同 Celestial Evolution Simulation 中的"：
新设置中的每个天体都通过原项目同款的 AddBodyDialog 输入，
同时通过 get_body_raw() 保留原始文本精度，供高精度计算使用。
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QSpinBox, QListWidget,
    QListWidgetItem, QMessageBox, QWidget, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt

from physics import Body, Mode
from .scientific_number_input import ScientificNumberInput
from .add_body_dialog import AddBodyDialog

# 默认模拟参数（与需求一致）
DEFAULT_DURATION = 60.0      # 模拟时长（时间单位 TU）
DEFAULT_DT = 0.0001          # 模拟时间步长
DEFAULT_PLAYBACK_SPEED = 1.0  # 播放速度（每秒渲染的标准时间数）


class SimulationParamsWidget(QGroupBox):
    """模拟时长 / 模拟时间步长 / 播放速度 / 计算精度（可选）"""

    def __init__(self, parent=None):
        super().__init__("模拟参数", parent)
        layout = QFormLayout(self)

        self.duration_input = ScientificNumberInput(
            value=DEFAULT_DURATION, min_value=1e-12, max_value=1e15,
            suffix=" TU",
        )
        layout.addRow("模拟时长:", self.duration_input)

        self.dt_input = ScientificNumberInput(
            value=DEFAULT_DT, min_value=1e-12, max_value=1e6,
            suffix=" TU",
        )
        layout.addRow("模拟时间步长:", self.dt_input)

        self.speed_input = ScientificNumberInput(
            value=DEFAULT_PLAYBACK_SPEED, min_value=1e-6, max_value=1e6,
            suffix=" TU/s",
        )
        layout.addRow("播放速度:", self.speed_input)

        self.digits_input = ScientificNumberInput(
            value=0.0, min_value=17.0, max_value=500.0,
        )
        self.digits_input.line_edit.setPlaceholderText("自动")
        self.digits_input.line_edit.setText("")
        layout.addRow("计算精度(有效位数,可选):", self.digits_input)

        hint = QLabel(
            "默认：模拟时长 60 TU，时间步长 0.0001，播放速度 1（每秒渲染 1 标准时间，60 帧/秒）。\n"
            "计算精度留空为自动：输入有效位数 ≤16 位时使用 float64；"
            "输入精度更高时自动切换 Decimal 高精度计算（默认 ≥50 位）。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addRow(hint)

    def values(self) -> dict:
        """返回 (duration, dt, playback_speed, requested_digits)"""
        digits_text = self.digits_input.raw_text()
        digits = None
        if digits_text:
            try:
                digits = int(float(digits_text))
                if digits < 17:
                    digits = None
            except (ValueError, TypeError):
                digits = None
        return {
            'duration': self.duration_input.value(),
            'dt': self.dt_input.value(),
            'playback_speed': self.speed_input.value(),
            'requested_digits': digits,
        }


class PresetSetupDialog(QDialog):
    """导入预设：选择预设 + 输入三个模拟参数"""

    def __init__(self, scenes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入预设")
        self.setMinimumWidth(480)
        self._scenes = scenes

        layout = QVBoxLayout(self)

        # 预设选择
        group = QGroupBox("选择预设")
        group_layout = QVBoxLayout(group)
        self.scene_combo = QComboBox()
        for s in scenes:
            self.scene_combo.addItem(s.get('name', '未命名'), s.get('path', ''))
        self.scene_combo.currentIndexChanged.connect(self._update_description)
        group_layout.addWidget(self.scene_combo)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #9ca3af;")
        group_layout.addWidget(self.desc_label)
        layout.addWidget(group)

        # 模拟参数
        self.params = SimulationParamsWidget()
        layout.addWidget(self.params)

        # 按钮
        btns = QHBoxLayout()
        ok = QPushButton("开始模拟")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        self._update_description()

    def _update_description(self):
        idx = self.scene_combo.currentIndex()
        if 0 <= idx < len(self._scenes):
            desc = self._scenes[idx].get('description', '')
            self.desc_label.setText(desc)

    def result_data(self) -> dict:
        idx = self.scene_combo.currentIndex()
        scene = self._scenes[idx] if 0 <= idx < len(self._scenes) else {}
        data = self.params.values()
        data.update({
            'scene_path': scene.get('path', ''),
            'scene_name': scene.get('name', ''),
            'source': 'preset',
        })
        return data


class NewSetupDialog(QDialog):
    """新设置：星体数 -> 逐个输入天体参数 -> 三个模拟参数"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新设置")
        self.setMinimumWidth(560)
        self._bodies: list[Body] = []
        self._entries: list[dict] = []

        layout = QVBoxLayout(self)

        # 单位模式
        unit_group = QGroupBox("输入单位")
        unit_layout = QHBoxLayout(unit_group)
        self._unit_mode = Mode.SIMULATION
        sim_radio = QRadioButton("模拟单位 (DU / MU / TU)")
        sim_radio.setChecked(True)
        sci_radio = QRadioButton("科学单位 (m / kg / AU / s)")
        self._unit_group = QButtonGroup(self)
        self._unit_group.addButton(sim_radio, 0)
        self._unit_group.addButton(sci_radio, 1)
        unit_layout.addWidget(sim_radio)
        unit_layout.addWidget(sci_radio)
        unit_layout.addStretch()
        layout.addWidget(unit_group)

        # 星体数
        count_group = QGroupBox("星体")
        count_layout = QHBoxLayout(count_group)
        count_layout.addWidget(QLabel("星体数:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(3)
        count_layout.addWidget(self.count_spin)
        count_layout.addWidget(QLabel("（默认 3）"))
        count_layout.addStretch()

        self.body_list = QListWidget()
        self.body_list.setMinimumHeight(140)
        count_layout2 = QVBoxLayout()
        count_layout2.addWidget(self.body_list)

        btn_row = QHBoxLayout()
        self.input_btn = QPushButton("逐个输入天体参数…")
        self.input_btn.clicked.connect(self._on_input_all)
        self.add_btn = QPushButton("添加一个")
        self.add_btn.clicked.connect(self._on_add_one)
        self.edit_btn = QPushButton("编辑选中")
        self.edit_btn.clicked.connect(self._on_edit_selected)
        self.del_btn = QPushButton("删除选中")
        self.del_btn.clicked.connect(self._on_delete_selected)
        for b in (self.input_btn, self.add_btn, self.edit_btn, self.del_btn):
            btn_row.addWidget(b)
        btn_row.addStretch()
        count_layout2.addLayout(btn_row)
        count_layout.addLayout(count_layout2, 1)
        layout.addWidget(count_group)

        # 模拟参数
        self.params = SimulationParamsWidget()
        layout.addWidget(self.params)

        # 按钮
        btns = QHBoxLayout()
        ok = QPushButton("开始模拟")
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        self._refresh_list()

    # ---- 单位模式 ----
    def _mode(self) -> Mode:
        return Mode.SCIENTIFIC if self._unit_group.checkedId() == 1 else Mode.SIMULATION

    # ---- 天体输入 ----
    def _dialog(self) -> AddBodyDialog:
        return AddBodyDialog(mode=self._mode(), parent=self)

    def _on_input_all(self):
        """按星体数逐个弹出输入对话框。"""
        target = self.count_spin.value()
        start = len(self._bodies)
        for _ in range(start, target):
            dlg = self._dialog()
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._bodies.append(dlg.get_body())
                self._entries.append(dlg.get_body_raw())
                self._refresh_list()
            else:
                break

    def _on_add_one(self):
        dlg = self._dialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._bodies.append(dlg.get_body())
            self._entries.append(dlg.get_body_raw())
            self._refresh_list()

    def _on_edit_selected(self):
        row = self.body_list.currentRow()
        if row < 0:
            return
        dlg = self._dialog()
        dlg.set_body(self._bodies[row])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._bodies[row] = dlg.get_body()
            self._entries[row] = dlg.get_body_raw()
            self._refresh_list()

    def _on_delete_selected(self):
        row = self.body_list.currentRow()
        if row >= 0:
            del self._bodies[row]
            del self._entries[row]
            self._refresh_list()

    def _refresh_list(self):
        self.body_list.clear()
        for i, b in enumerate(self._bodies):
            item = QListWidgetItem(
                f"#{i+1}  {b.name}  ·  m={b.mass:.6g}  ·  r=({b.position[0]:.6g}, {b.position[1]:.6g})"
            )
            item.setToolTip(f"速度: ({b.velocity[0]:.6g}, {b.velocity[1]:.6g})")
            self.body_list.addItem(item)
        self.body_list.setCurrentRow(-1)

    def _on_ok(self):
        target = self.count_spin.value()
        if len(self._bodies) < target:
            answer = QMessageBox.question(
                self, "天体数量不足",
                f"已输入 {len(self._bodies)} 个天体，目标为 {target} 个。\n"
                "是否继续逐个输入剩余天体？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._on_input_all()
        if len(self._bodies) == 0:
            QMessageBox.warning(self, "没有天体", "请至少输入一个天体。")
            return
        self.accept()

    def result_data(self) -> dict:
        data = self.params.values()
        data.update({
            'bodies': list(self._bodies),
            'entries': list(self._entries),
            'source': 'new',
            'unit_mode': self._mode().display_name,
        })
        return data

