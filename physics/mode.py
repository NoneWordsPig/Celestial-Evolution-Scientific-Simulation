"""
模拟模式枚举模块

定义 Mode 枚举，控制 UI 显示层行为。

重要原则：
- Physics Engine 不感知 Mode
- Mode 仅影响单位显示格式、UI 信息密度、用户输入方式
- 两种模式使用完全相同的物理引擎和数据
"""

from enum import Enum, auto


class Mode(Enum):
    """
    模拟模式枚举

    SIMULATION:
        简洁显示，使用模拟单位 MU / DU / TU
        突出天体运动、轨迹、暂停、时间倍率
        允许视觉增强

    SCIENTIFIC:
        详细科学信息面板
        若有现实单位映射则显示现实单位（kg, m, km/s）
        若无映射则仍显示 MU / DU / TU 并提示
        显示能量、动量、质心等物理量
    """
    SIMULATION = auto()
    SCIENTIFIC = auto()

    @property
    def is_simulation(self) -> bool:
        """是否为模拟模式"""
        return self is Mode.SIMULATION

    @property
    def is_scientific(self) -> bool:
        """是否为科学模式"""
        return self is Mode.SCIENTIFIC

    @property
    def display_name(self) -> str:
        """模式显示名称"""
        if self is Mode.SIMULATION:
            return "\u6a21\u62df"
        return "\u79d1\u5b66"
