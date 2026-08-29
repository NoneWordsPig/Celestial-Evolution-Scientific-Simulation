"""
单位格式化器模块

提供 SimulationFormatter 和 ScientificFormatter，
将 Physics Engine 输出的模拟单位数值格式化为显示字符串。

UI 层不直接进行单位转换，而是通过 Formatter 获取格式化后的字符串。

Physics Engine 内部始终使用模拟单位（MU, DU, TU）。
Formatter 只负责显示层的格式化。
"""

import math
from typing import Optional
import numpy as np

from .units import UnitSystem, UnitConverter


# ============================================================
# Unicode 上标数字映射
# ============================================================
_SUPERSCRIPT_DIGITS = {
    '0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3',
    '4': '\u2074', '5': '\u2075', '6': '\u2076', '7': '\u2077',
    '8': '\u2078', '9': '\u2079', '-': '\u207b',
}


def _to_superscript(number: int) -> str:
    """将整数转换为 Unicode 上标字符串"""
    return ''.join(_SUPERSCRIPT_DIGITS.get(d, d) for d in str(number))


def _scientific_notation(value: float, unit: str, precision: int = 3) -> str:
    """
    将数值格式化为科学计数法字符串

    例如：1.989 × 10³⁰ kg

    Args:
        value: 数值
        unit: 单位字符串
        precision: 有效数字位数

    Returns:
        格式化字符串
    """
    if value == 0.0:
        return f"0.000 {unit}"

    negative = value < 0.0
    abs_value = abs(value)
    exponent = int(math.floor(math.log10(abs_value)))
    mantissa = abs_value / (10.0 ** exponent)

    sign = "-" if negative else ""
    sup_exp = _to_superscript(exponent)

    return f"{sign}{mantissa:.{precision - 1}f} \u00d7 10{sup_exp} {unit}"


class SimulationFormatter:
    """
    模拟模式格式化器

    使用简洁的模拟单位显示：MU, DU, TU, DU/TU
    避免科学计数法，直接显示数值
    """

    def __init__(self, unit_system: Optional[UnitSystem] = None):
        """
        初始化模拟模式格式化器

        Args:
            unit_system: 单位系统实例，默认使用标准模拟单位
        """
        self.units = unit_system or UnitSystem()

    def format_mass(self, value: float, precision: int = 2) -> str:
        """
        格式化质量

        Args:
            value: 质量 (MU)
            precision: 小数位数

        Returns:
            例如 "1000.00 MU"
        """
        return f"{value:.{precision}f} {self.units.mass_unit}"

    def format_distance(self, value: float, precision: int = 2) -> str:
        """
        格式化距离

        Args:
            value: 距离 (DU)
            precision: 小数位数

        Returns:
            例如 "10.00 DU"
        """
        return f"{value:.{precision}f} {self.units.distance_unit}"

    def format_position(self, x: float, y: float, precision: int = 2) -> str:
        """
        格式化位置坐标

        Args:
            x: X 坐标 (DU)
            y: Y 坐标 (DU)
            precision: 小数位数

        Returns:
            例如 "X: 10.00 DU  Y: 0.00 DU"
        """
        du = self.units.distance_unit
        return f"X: {x:.{precision}f} {du}  Y: {y:.{precision}f} {du}"

    def format_velocity(self, value: float, precision: int = 2) -> str:
        """
        格式化速度标量

        Args:
            value: 速度 (DU/TU)
            precision: 小数位数

        Returns:
            例如 "10.00 DU/TU"
        """
        return f"{value:.{precision}f} {self.units.velocity_unit}"

    def format_velocity_vector(self, vx: float, vy: float, precision: int = 2) -> str:
        """
        格式化速度向量

        Args:
            vx: X 分量 (DU/TU)
            vy: Y 分量 (DU/TU)
            precision: 小数位数

        Returns:
            例如 "Vx: 0.00 DU/TU  Vy: 10.00 DU/TU"
        """
        vu = self.units.velocity_unit
        return f"Vx: {vx:.{precision}f} {vu}  Vy: {vy:.{precision}f} {vu}"

    def format_time(self, value: float, precision: int = 2) -> str:
        """
        格式化时间

        Args:
            value: 时间 (TU)
            precision: 小数位数

        Returns:
            例如 "12.50 TU"
        """
        return f"{value:.{precision}f} {self.units.time_unit}"

    def format_energy(self, value: float, precision: int = 2) -> str:
        """
        格式化能量

        模拟单位中能量单位为 MU * (DU/TU)^2

        Args:
            value: 能量
            precision: 小数位数

        Returns:
            例如 "-500.00 MU*(DU/TU)²"
        """
        unit = f"{self.units.mass_unit}*({self.units.velocity_unit})\u00b2"
        return f"{value:.{precision}f} {unit}"

    def format_momentum(self, px: float, py: float, precision: int = 2) -> str:
        """
        格式化动量向量

        模拟单位中动量单位为 MU * DU/TU

        Args:
            px: X 分量
            py: Y 分量
            precision: 小数位数

        Returns:
            例如 "Px: 0.00  Py: 10.00 MU*DU/TU"
        """
        unit = f"{self.units.mass_unit}*{self.units.velocity_unit}"
        return f"Px: {px:.{precision}f}  Py: {py:.{precision}f} {unit}"

    def format_force(self, fx: float, fy: float, precision: int = 4) -> str:
        """
        格式化力向量

        Args:
            fx: X 分量
            fy: Y 分量
            precision: 小数位数

        Returns:
            格式化字符串
        """
        return f"Fx: {fx:.{precision}f}  Fy: {fy:.{precision}f}"


class ScientificFormatter:
    """
    科学模式格式化器

    如果存在现实单位映射（UnitConverter），则显示现实单位：
        kg, m, km/s, days/years

    如果不存在现实单位映射，则回退到模拟单位显示，
    并附带提示信息。
    """

    def __init__(
        self,
        unit_system: Optional[UnitSystem] = None,
        converter: Optional[UnitConverter] = None
    ):
        """
        初始化科学模式格式化器

        Args:
            unit_system: 单位系统实例
            converter: 现实单位转换器（可选）
        """
        self.units = unit_system or UnitSystem()
        self.converter = converter

    @property
    def has_real_mapping(self) -> bool:
        """是否存在现实单位映射"""
        return self.converter is not None

    def _fallback_warning(self) -> str:
        """无现实映射时的提示信息"""
        return "\u5f53\u524d\u672a\u8bbe\u7f6e\u73b0\u5b9e\u4e16\u754c\u5355\u4f4d\u6620\u5c04"

    def format_mass(self, value: float, precision: int = 3) -> str:
        """
        格式化质量

        有映射：显示现实单位（如 "1.989 \u00d7 10\u00b3\u2070 kg"）
        无映射：显示模拟单位 + 提示

        Args:
            value: 质量 (MU)
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            real_mass = self.converter.sim_to_real_mass(value)
            return _scientific_notation(real_mass, self.converter.real_mass_unit, precision)
        return f"{value:.{precision}f} {self.units.mass_unit}  ({self._fallback_warning()})"

    def format_distance(self, value: float, precision: int = 3) -> str:
        """
        格式化距离

        有映射：显示现实单位（如 "1.496 \u00d7 10\u00b9\u00b9 m"）
        无映射：显示模拟单位 + 提示

        Args:
            value: 距离 (DU)
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            real_dist = self.converter.sim_to_real_distance(value)
            return _scientific_notation(real_dist, self.converter.real_distance_unit, precision)
        return f"{value:.{precision}f} {self.units.distance_unit}  ({self._fallback_warning()})"

    def format_position(self, x: float, y: float, precision: int = 3) -> str:
        """
        格式化位置坐标

        Args:
            x: X 坐标 (DU)
            y: Y 坐标 (DU)
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            real_x = self.converter.sim_to_real_distance(x)
            real_y = self.converter.sim_to_real_distance(y)
            unit = self.converter.real_distance_unit
            return (f"X: {_scientific_notation(real_x, unit, precision)}  "
                    f"Y: {_scientific_notation(real_y, unit, precision)}")
        du = self.units.distance_unit
        return (f"X: {x:.{precision}f} {du}  Y: {y:.{precision}f} {du}"
                f"  ({self._fallback_warning()})")

    def format_velocity(self, value: float, precision: int = 2) -> str:
        """
        格式化速度标量

        有映射：显示 km/s（自动选择合适单位）
        无映射：显示模拟单位 + 提示

        Args:
            value: 速度 (DU/TU)
            precision: 小数位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            real_v = self.converter.sim_to_real_velocity(value)
            if abs(real_v) >= 1000.0:
                return f"{real_v / 1000.0:.{precision}f} km/s"
            return f"{real_v:.{precision}f} m/s"
        return f"{value:.{precision}f} {self.units.velocity_unit}  ({self._fallback_warning()})"

    def format_velocity_vector(self, vx: float, vy: float, precision: int = 2) -> str:
        """
        格式化速度向量

        Args:
            vx: X 分量 (DU/TU)
            vy: Y 分量 (DU/TU)
            precision: 小数位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            real_vx = self.converter.sim_to_real_velocity(vx)
            real_vy = self.converter.sim_to_real_velocity(vy)
            if max(abs(real_vx), abs(real_vy)) >= 1000.0:
                return f"Vx: {real_vx/1000.0:.{precision}f} km/s  Vy: {real_vy/1000.0:.{precision}f} km/s"
            return f"Vx: {real_vx:.{precision}f} m/s  Vy: {real_vy:.{precision}f} m/s"
        vu = self.units.velocity_unit
        return (f"Vx: {vx:.{precision}f} {vu}  Vy: {vy:.{precision}f} {vu}"
                f"  ({self._fallback_warning()})")

    def format_time(self, value: float, precision: int = 2) -> str:
        """
        格式化时间

        有映射：自动选择 days / years
        无映射：显示模拟单位 + 提示

        Args:
            value: 时间 (TU)
            precision: 小数位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            return self.converter.format_real_time(value)
        return f"{value:.{precision}f} {self.units.time_unit}  ({self._fallback_warning()})"

    def format_energy(self, value: float, precision: int = 3) -> str:
        """
        格式化能量

        有映射：转换为焦耳 (J) 并显示科学计数法
        无映射：显示模拟单位

        能量转换：
        E_real = E_sim * MU_real * (DU_real / TU_real)^2
              = E_sim * MU_real * VU_real^2

        Args:
            value: 能量 (模拟单位)
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            energy_factor = (self.converter.real_mass_per_MU *
                           self.converter.real_velocity_per_VU ** 2)
            real_energy = value * energy_factor
            return _scientific_notation(real_energy, "J", precision)
        unit = f"{self.units.mass_unit}*({self.units.velocity_unit})\u00b2"
        return f"{value:.{precision}f} {unit}"

    def format_momentum(self, px: float, py: float, precision: int = 3) -> str:
        """
        格式化动量向量

        有映射：转换为 kg*m/s
        无映射：显示模拟单位

        Args:
            px: X 分量 (MU * DU/TU)
            py: Y 分量 (MU * DU/TU)
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            mom_factor = (self.converter.real_mass_per_MU *
                         self.converter.real_velocity_per_VU)
            real_px = px * mom_factor
            real_py = py * mom_factor
            return (f"Px: {_scientific_notation(real_px, 'kg*m/s', precision)}  "
                    f"Py: {_scientific_notation(real_py, 'kg*m/s', precision)}")
        unit = f"{self.units.mass_unit}*{self.units.velocity_unit}"
        return f"Px: {px:.{precision}f}  Py: {py:.{precision}f} {unit}"

    def format_force(self, fx: float, fy: float, precision: int = 3) -> str:
        """
        格式化力向量

        Args:
            fx: X 分量
            fy: Y 分量
            precision: 有效数字位数

        Returns:
            格式化字符串
        """
        if self.converter is not None:
            force_factor = (self.converter.real_mass_per_MU *
                          self.converter.real_velocity_per_VU /
                          self.converter.real_time_per_TU)
            real_fx = fx * force_factor
            real_fy = fy * force_factor
            return (f"Fx: {_scientific_notation(real_fx, 'N', precision)}  "
                    f"Fy: {_scientific_notation(real_fy, 'N', precision)}")
        return f"Fx: {fx:.{precision}f}  Fy: {fy:.{precision}f}"
