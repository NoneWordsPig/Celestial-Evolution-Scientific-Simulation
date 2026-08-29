"""
统一 UI 样式系统

深色宇宙主题 - 现代科技风格
"""


# 主色调 - 蓝紫色系
PRIMARY_COLOR = "#6366F1"  # 靛蓝色
PRIMARY_HOVER = "#4F46E5"
PRIMARY_PRESSED = "#4338CA"

SECONDARY_COLOR = "#8B5CF6"  # 紫色
SECONDARY_HOVER = "#7C3AED"
SECONDARY_PRESSED = "#6D28D9"

ACCENT_COLOR = "#06B6D4"  # 青色高亮

DANGER_COLOR = "#EF4444"
DANGER_HOVER = "#DC2626"
DANGER_PRESSED = "#B91C1C"

SUCCESS_COLOR = "#10B981"
SUCCESS_HOVER = "#059669"
SUCCESS_PRESSED = "#047857"

# 背景色 - 深色宇宙主题
BG_COLOR = "#0A0E1A"  # 深空黑
BG_LIGHT = "#141824"  # 面板背景
BG_LIGHTER = "#1E2333"  # 悬浮背景
BG_DARK = "#050810"  # 更深背景

# 文字颜色
TEXT_PRIMARY = "#E5E7EB"
TEXT_SECONDARY = "#9CA3AF"
TEXT_DISABLED = "#4B5563"

# 边框
BORDER_COLOR = "#2D3348"
BORDER_FOCUS = PRIMARY_COLOR

# 透明度
PANEL_OPACITY = "0.85"


# 全局面板样式
PANEL_STYLE = f"""
/* 主窗口 */
QMainWindow {{
    background-color: {BG_COLOR};
}}

/* 中心部件 */
QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
}}

/* 菜单栏 */
QMenuBar {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER_COLOR};
    padding: 2px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {PRIMARY_COLOR};
}}

QMenu {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {PRIMARY_COLOR};
}}

/* 工具栏 */
QToolBar {{
    background-color: {BG_LIGHT};
    border-bottom: 1px solid {BORDER_COLOR};
    spacing: 8px;
    padding: 6px;
}}

/* 状态栏 */
QStatusBar {{
    background-color: {BG_LIGHT};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_COLOR};
    padding: 4px;
}}

QStatusBar::item {{
    border: none;
}}

/* 分组框 */
QGroupBox {{
    background-color: {BG_LIGHT};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    padding-top: 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {PRIMARY_COLOR};
}}

/* 标签 */
QLabel {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
    padding: 2px;
}}

/* 列表控件 */
QListWidget {{
    background-color: {BG_LIGHT};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    outline: none;
}}

QListWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    margin: 2px;
}}

QListWidget::item:selected {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}

QListWidget::item:hover {{
    background-color: {BG_LIGHTER};
}}

/* 输入框 */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {BG_LIGHTER};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px;
    color: {TEXT_PRIMARY};
    selection-background-color: {PRIMARY_COLOR};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {BORDER_FOCUS};
}}

/* 下拉框 */
QComboBox {{
    background-color: {BG_LIGHTER};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    color: {TEXT_PRIMARY};
    min-width: 80px;
}}

QComboBox:hover {{
    border-color: {PRIMARY_COLOR};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_LIGHT};
    border: 1px solid {BORDER_COLOR};
    color: {TEXT_PRIMARY};
    selection-background-color: {PRIMARY_COLOR};
    border-radius: 4px;
}}

/* 滚动条 */
QScrollBar:vertical {{
    background-color: {BG_COLOR};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {SECONDARY_COLOR};
    min-height: 30px;
    border-radius: 5px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {SECONDARY_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {BG_COLOR};
    height: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {SECONDARY_COLOR};
    min-width: 30px;
    border-radius: 5px;
    margin: 2px;
}}

/* 分割器 */
QSplitter::handle {{
    background-color: {BORDER_COLOR};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {PRIMARY_COLOR};
}}

/* 复选框 */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {BORDER_COLOR};
    border-radius: 4px;
    background-color: {BG_LIGHTER};
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
}}

QCheckBox::indicator:hover {{
    border-color: {PRIMARY_COLOR};
}}

/* 滑块 */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {BG_LIGHTER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: {PRIMARY_COLOR};
    border: none;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {PRIMARY_HOVER};
}}

/* 工具提示 */
QToolTip {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""


# 通用按钮样式
BUTTON_STYLE = f"""
QPushButton {{
    background-color: {BG_LIGHTER};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {SECONDARY_HOVER};
    border-color: {SECONDARY_HOVER};
}}

QPushButton:pressed {{
    background-color: {SECONDARY_PRESSED};
}}

QPushButton:disabled {{
    background-color: {BG_LIGHT};
    color: {TEXT_DISABLED};
    border-color: {BORDER_COLOR};
}}
"""

# 主要按钮样式（蓝色）
PRIMARY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {PRIMARY_HOVER};
}}

QPushButton:pressed {{
    background-color: {PRIMARY_PRESSED};
}}

QPushButton:disabled {{
    background-color: {BG_LIGHTER};
    color: {TEXT_DISABLED};
}}
"""

# 危险按钮样式（红色）
DANGER_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {DANGER_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {DANGER_HOVER};
}}

QPushButton:pressed {{
    background-color: {DANGER_PRESSED};
}}

QPushButton:disabled {{
    background-color: {BG_LIGHTER};
    color: {TEXT_DISABLED};
}}
"""

# 成功按钮样式（绿色）
SUCCESS_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {SUCCESS_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton:hover {{
    background-color: {SUCCESS_HOVER};
}}

QPushButton:pressed {{
    background-color: {SUCCESS_PRESSED};
}}

QPushButton:disabled {{
    background-color: {BG_LIGHTER};
    color: {TEXT_DISABLED};
}}
"""

# 工具栏按钮样式（紧凑）
TOOLBAR_BUTTON_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {BG_LIGHTER};
    border-color: {PRIMARY_COLOR};
    color: {PRIMARY_COLOR};
}}

QPushButton:pressed {{
    background-color: {PRIMARY_COLOR};
    color: white;
}}

QPushButton:checked {{
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
    color: white;
}}

QPushButton:disabled {{
    color: {TEXT_DISABLED};
    border-color: {BORDER_COLOR};
}}
"""


def apply_global_style(app):
    """
    应用全局样式到应用程序
    
    Args:
        app: QApplication 实例
    """
    app.setStyleSheet(PANEL_STYLE)


def apply_button_style(button, style_type='default'):
    """
    应用按钮样式
    
    Args:
        button: QPushButton 实例
        style_type: 'default', 'primary', 'danger', 'success', 'toolbar'
    """
    if style_type == 'primary':
        button.setStyleSheet(PRIMARY_BUTTON_STYLE)
    elif style_type == 'danger':
        button.setStyleSheet(DANGER_BUTTON_STYLE)
    elif style_type == 'success':
        button.setStyleSheet(SUCCESS_BUTTON_STYLE)
    elif style_type == 'toolbar':
        button.setStyleSheet(TOOLBAR_BUTTON_STYLE)
    else:
        button.setStyleSheet(BUTTON_STYLE)
