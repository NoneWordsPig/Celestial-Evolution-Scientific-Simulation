"""
Body List Widget

左侧天体列表，显示所有天体
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from physics import PhysicsEngine, SimulationFormatter, ScientificFormatter, Mode, UnitSystem, UnitConverter


class BodyListWidget(QWidget):
    """
    天体列表组件
    
    显示所有天体，支持选择和删除
    """
    
    # 信号
    body_selected = pyqtSignal(int)  # 天体被选中
    body_delete_requested = pyqtSignal(int)  # 请求删除天体
    
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
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("天体列表")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)
        
        # 删除按钮
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)
        
        # 信息标签
        self.info_label = QLabel("共 0 个天体")
        layout.addWidget(self.info_label)
    
    def refresh(self):
        """刷新列表"""
        current_row = self.list_widget.currentRow()
        self.list_widget.clear()
        
        # 选择格式化器
        if self.mode == Mode.SIMULATION:
            formatter = SimulationFormatter(self.unit_system)
        else:
            formatter = ScientificFormatter(self.unit_system, self.converter)
        
        # 添加天体
        for i, body in enumerate(self.engine.bodies):
            mass_str = formatter.format_mass(body.mass, precision=1)
            text = f"{body.name}\n{mass_str}"
            
            item = QListWidgetItem(text)
            
            # 设置颜色
            color = body.color
            qcolor = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
            item.setForeground(qcolor)
            
            self.list_widget.addItem(item)
        
        # 恢复选择
        if 0 <= current_row < len(self.engine.bodies):
            self.list_widget.setCurrentRow(current_row)
        
        # 更新信息
        self.info_label.setText(f"共 {len(self.engine.bodies)} 个天体")
    
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
    
    def _on_selection_changed(self):
        """选择变化"""
        row = self.list_widget.currentRow()
        self.delete_btn.setEnabled(row >= 0)
        if row >= 0:
            self.body_selected.emit(row)
    
    def _on_delete_clicked(self):
        """删除按钮点击"""
        row = self.list_widget.currentRow()
        if row >= 0:
            self.body_delete_requested.emit(row)
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Delete:
            row = self.list_widget.currentRow()
            if row >= 0:
                self.body_delete_requested.emit(row)
        else:
            super().keyPressEvent(event)
