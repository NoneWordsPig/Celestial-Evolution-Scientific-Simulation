"""
动态比例尺模块

根据 Camera.zoom 自动计算合适的比例尺
使用 1-2-5 系列：1, 2, 5, 10, 20, 50, 100, ...
"""

import math
from typing import Tuple
from .camera import Camera
from .mode import Mode
from .units import UnitSystem, UnitConverter
from .formatter import SimulationFormatter, ScientificFormatter


def compute_nice_number(value: float) -> float:
    """
    计算 1-2-5 序列中的"好看"数字
    
    算法：
    1. 将 value 归一化到 [1, 10) 范围
    2. 根据归一化值选择 1, 2, 5
    3. 乘以 10 的幂次
    
    Args:
        value: 输入值（必须 > 0）
        
    Returns:
        1-2-5 序列中的值
    """
    if value <= 0:
        return 1.0
    
    # 计算 10 的幂次
    exponent = math.floor(math.log10(value))
    fraction = value / (10 ** exponent)
    
    # 选择 1, 2, 5
    if fraction < 1.5:
        nice_fraction = 1.0
    elif fraction < 3.5:
        nice_fraction = 2.0
    elif fraction < 7.5:
        nice_fraction = 5.0
    else:
        nice_fraction = 10.0
    
    return nice_fraction * (10 ** exponent)


def _adaptive_decimal_precision(value: float) -> int:
    """
    根据数值量级自适应小数位数

    当数值 < 1 时保留足够的小数位，避免固定 precision=0
    把 0.5 DU / 0.1 DU 显示成 "0 DU"。
    """
    if value <= 0:
        return 1
    if value >= 1.0:
        return 0
    return max(1, -math.floor(math.log10(value)))


class ScaleBar:
    """
    动态比例尺
    
    根据 Camera.zoom 自动计算合适的比例尺值和像素长度
    """
    
    def __init__(
        self,
        target_pixel_length: float = 150.0,
        min_pixel_length: float = 80.0,
        max_pixel_length: float = 250.0
    ):
        """
        初始化比例尺
        
        Args:
            target_pixel_length: 目标像素长度（约 100-200 px）
            min_pixel_length: 最小像素长度
            max_pixel_length: 最大像素长度
        """
        self.target_pixel_length = target_pixel_length
        self.min_pixel_length = min_pixel_length
        self.max_pixel_length = max_pixel_length
    
    def compute(
        self,
        camera: Camera,
        mode: Mode = Mode.SIMULATION,
        unit_system: UnitSystem = None,
        converter: UnitConverter = None
    ) -> Tuple[float, float, str]:
        """
        计算比例尺
        
        Args:
            camera: 摄像机实例
            mode: 当前模式
            unit_system: 单位系统（模拟模式）
            converter: 单位转换器（科学模式，可选）
            
        Returns:
            (world_distance, pixel_length, label)
            - world_distance: 比例尺对应的世界距离（DU 或现实单位）
            - pixel_length: 比例尺的像素长度
            - label: 显示标签（如 "10 DU" 或 "1 AU"）
        """
        if unit_system is None:
            unit_system = UnitSystem()
        
        # 计算目标世界距离（target_pixel_length 像素对应的世界距离）
        target_world_distance = self.target_pixel_length / camera.zoom
        
        # 使用 1-2-5 序列找到"好看"的世界距离
        nice_world_distance = compute_nice_number(target_world_distance)
        
        # 计算实际像素长度
        pixel_length = nice_world_distance * camera.zoom
        
        # 确保像素长度在合理范围内
        if pixel_length < self.min_pixel_length:
            # 尝试更大的世界距离
            nice_world_distance = compute_nice_number(
                self.min_pixel_length / camera.zoom
            )
            pixel_length = nice_world_distance * camera.zoom
        
        if pixel_length > self.max_pixel_length:
            # 尝试更小的世界距离
            nice_world_distance = compute_nice_number(
                self.max_pixel_length / camera.zoom
            )
            pixel_length = nice_world_distance * camera.zoom
        
        # 生成标签
        if mode == Mode.SIMULATION:
            # 模拟模式：显示 DU（小数位数随量级自适应，<1 DU 不丢精度）
            formatter = SimulationFormatter(unit_system)
            label = formatter.format_distance(
                nice_world_distance,
                precision=_adaptive_decimal_precision(nice_world_distance),
            )
        else:
            # 科学模式
            if converter is not None:
                # 有现实映射：转换为现实单位（科学计数法，无小数位问题）
                formatter = ScientificFormatter(converter=converter)
                real_distance = converter.sim_to_real_distance(nice_world_distance)
                label = formatter.format_distance(real_distance, precision=2)
            else:
                # 无映射：显示 DU + 提示（同样自适应小数位数）
                formatter = ScientificFormatter()
                label = formatter.format_distance(
                    nice_world_distance,
                    precision=_adaptive_decimal_precision(nice_world_distance),
                )
        
        return nice_world_distance, pixel_length, label
