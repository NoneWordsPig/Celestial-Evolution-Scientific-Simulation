"""
独立 UnitSystem 模块

基于 Scientific Normalization 建立模拟单位系统：

    L0 = 1 AU
    M0 = 1 M_sun
    T0 = sqrt(L0^3 / (G_SI * M0))
    G_SI = 6.67430e-11

使 G_sim = 1。所有现实单位转换统一进入 normalized simulation units
（DU / MU / TU / DU·TU^-1 / DU·TU^-2），
Physics Engine 永远只接收 normalized values（G = 1）。

本模块完全独立，不依赖 UI / Physics Engine / Renderer。
"""

import math
import re

__all__ = [
    'UnitSystem',
    'G_SI', 'AU', 'SOLAR_MASS', 'DAY', 'YEAR',
]


# ============================================================
# 科学归一化常量（SI）
# ============================================================

# 万有引力常数（m^3 kg^-1 s^-2）
G_SI = 6.67430e-11

# 标准长度：1 AU（m，IAU 定义值）
AU = 1.495978707e11

# 标准质量：1 太阳质量（kg）
SOLAR_MASS = 1.98892e30

# 时间单位换算（s）
DAY = 86400.0
YEAR = 365.25 * DAY  # 儒略年


def _normalize_unit(unit):
    """规范化单位字符串为注册表键（大小写、上标、空格不敏感）"""
    if unit is None:
        return None
    s = str(unit).strip().lower()
    if not s:
        return None
    s = s.replace('²', '2').replace('^', '').replace(' ', '')
    return _ALIASES.get(s)


_ALIASES = {
    # 长度
    'm': 'm',
    'km': 'km',
    'au': 'au',
    # 质量
    'kg': 'kg',
    'm_sun': 'm_sun',
    'msun': 'm_sun',
    'solar_mass': 'm_sun',
    # 时间
    's': 's',
    'sec': 's',
    'second': 's',
    'seconds': 's',
    'day': 'day',
    'days': 'day',
    'year': 'year',
    'years': 'year',
    'yr': 'year',
    # 速度
    'm/s': 'm/s',
    'km/s': 'km/s',
    'au/t0': 'au/t0',
    # 加速度
    'm/s2': 'm/s2',
    'km/s2': 'km/s2',
    # 归一化模拟单位（身份映射）
    'du': 'du',
    'mu': 'mu',
    'tu': 'tu',
    'du/tu': 'du/tu',
    'du/tu2': 'du/tu2',
}


def _format_number(value, precision=15):
    """格式化浮点数：约 precision 位有效数字，指数不补零"""
    v = float(value)
    if v == 0.0:
        return '0'
    text = format(v, f'.{precision}g')
    if float(text) != v:
        text = repr(v)
    low = text.lower()
    if 'e' not in low:
        return text
    mantissa, _, exp = low.partition('e')
    return f"{mantissa}e{int(exp)}"


class UnitSystem:
    """
    独立科学归一化单位系统

    默认归一化：
        L0 = 1 AU
        M0 = 1 M_sun
        T0 = sqrt(L0^3 / (G_SI * M0))

    由此推导：
        V0 = L0 / T0（标准速度，m/s）
        A0 = L0 / T0^2（标准加速度，m/s^2）

    接口：
        parse(text)                 -> (value, unit)
        format(value, unit)         -> "数值 单位" 字符串
        to_simulation(value, unit)  -> normalized simulation value
        from_simulation(value, unit)-> 指定现实单位的数值
    """

    def __init__(self, L0=AU, M0=SOLAR_MASS, G_SI=G_SI):
        self.G_SI = float(G_SI)
        self.L0 = float(L0)          # 标准长度（m）
        self.M0 = float(M0)          # 标准质量（kg）
        # 标准时间：使 G_sim = L0^3 / (T0^2 * M0) = 1
        self.T0 = math.sqrt(self.L0 ** 3 / (self.G_SI * self.M0))
        self.V0 = self.L0 / self.T0  # 标准速度（m/s）
        self.A0 = self.L0 / self.T0 ** 2  # 标准加速度（m/s^2）
        self.G_sim = 1.0

        # 各维度：1 单位 SI 对应的归一化模拟单位数
        self._sim_per_si = {
            'length': 1.0 / self.L0,
            'mass': 1.0 / self.M0,
            'time': 1.0 / self.T0,
            'velocity': 1.0 / self.V0,
            'acceleration': 1.0 / self.A0,
        }

        # 注册表：key -> (维度, 该单位对应的 SI 系数, 规范显示名)
        self._units = {
            # 长度
            'm': ('length', 1.0, 'm'),
            'km': ('length', 1.0e3, 'km'),
            'au': ('length', self.L0, 'AU'),
            # 质量
            'kg': ('mass', 1.0, 'kg'),
            'm_sun': ('mass', self.M0, 'M_sun'),
            # 时间
            's': ('time', 1.0, 's'),
            'day': ('time', DAY, 'day'),
            'year': ('time', YEAR, 'year'),
            # 速度
            'm/s': ('velocity', 1.0, 'm/s'),
            'km/s': ('velocity', 1.0e3, 'km/s'),
            'au/t0': ('velocity', self.V0, 'AU/T0'),
            # 加速度
            'm/s2': ('acceleration', 1.0, 'm/s²'),
            'km/s2': ('acceleration', 1.0e3, 'km/s²'),
            # 归一化模拟单位（身份映射）
            'du': ('length', self.L0, 'DU'),
            'mu': ('mass', self.M0, 'MU'),
            'tu': ('time', self.T0, 'TU'),
            'du/tu': ('velocity', self.V0, 'DU/TU'),
            'du/tu2': ('acceleration', self.A0, 'DU/TU²'),
        }

        # 预计算合成因子：sim = value * factor；factor = SI系数 / 归一化基
        # 数学上恒等于 1 的单位（AU、M_sun、DU、TU 等）钳位为精确 1.0，
        # 避免 L0 * (1/L0) 这类浮点舍入在恒等转换中引入 1e-16 误差。
        self._factor = {}
        for key, (dim, si_factor, _) in self._units.items():
            factor = si_factor * self._sim_per_si[dim]
            if math.isclose(factor, 1.0, rel_tol=1e-12):
                factor = 1.0
            self._factor[key] = factor

    # ============================================================
    # 解析 / 格式化
    # ============================================================

    _NUM_RE = re.compile(
        r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*?)\s*$'
    )

    def parse(self, text):
        """
        解析 "数值 单位" 字符串（如 "5.972e24 kg"、"1 AU"、"3.003e-6"）。

        Returns:
            (value: float, unit: str)
            无单位时 unit 为空字符串，表示已是归一化模拟单位。
        """
        m = self._NUM_RE.match(str(text))
        if m is None:
            raise ValueError(f"无法解析数值输入: {text!r}")
        value = float(m.group(1))
        unit_text = m.group(2).strip()
        key = _normalize_unit(unit_text)
        if key is None:
            if unit_text:
                raise ValueError(f"不支持的物理单位: {unit_text!r}")
            return value, ""
        return value, self._units[key][2]

    def format(self, value, unit="", precision=15):
        """
        将归一化模拟数值格式化为 "数值 单位" 字符串。

        Args:
            value: normalized simulation value
            unit: 目标现实单位（或空字符串表示模拟单位）
            precision: 有效数字位数（默认约 15 位）
        """
        real = self.from_simulation(value, unit)
        key = _normalize_unit(unit)
        display = self._units[key][2] if key is not None else ""
        text = _format_number(real, precision)
        return f"{text} {display}".strip()

    # ============================================================
    # 转换
    # ============================================================

    def to_simulation(self, value, unit):
        """
        现实单位数值 -> normalized simulation units（G = 1）。

        例：to_simulation(1.0, 'AU') == 1.0 DU
            to_simulation(1.0, 'M_sun') == 1.0 MU
            to_simulation(5.972e24, 'kg') ≈ 3.003e-6 MU
            to_simulation(1.0, 'year') ≈ 2π TU
        """
        value = float(value)
        key = _normalize_unit(unit)
        if key is None:
            # 无单位：视为已是归一化模拟单位
            return value
        if key not in self._units:
            raise ValueError(f"不支持的物理单位: {unit!r}")
        return value * self._factor[key]

    def from_simulation(self, value, unit):
        """
        normalized simulation units -> 指定现实单位数值。

        例：from_simulation(1.0, 'AU') == 1.0 AU
            from_simulation(3.003e-6, 'kg') ≈ 5.972e24 kg
            from_simulation(2π, 'year') ≈ 1.0 year
        """
        value = float(value)
        key = _normalize_unit(unit)
        if key is None:
            return value
        if key not in self._units:
            raise ValueError(f"不支持的物理单位: {unit!r}")
        return value / self._factor[key]
