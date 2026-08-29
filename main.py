"""
天体科学模拟器 - 主入口

进入主界面后直接显示"导入预设"与"新设置"两个选项模块。
"""

import sys

from PyQt6.QtWidgets import QApplication

from ui.styles import apply_global_style
from ui.startup_window import StartupWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    apply_global_style(app)

    window = StartupWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
