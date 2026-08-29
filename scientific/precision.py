"""
高精度数值支持模块

设计原则：
- 模拟单位（DU / MU / TU）下，位置、速度、质量、半径等输入可携带任意有效位数。
- 自动精度检测：若所有输入均可被 float64 无损表示（"输入精度较小时"），
  使用常规 16 位精度（float64 + NumPy 快速路径）；
  否则启用 Decimal 高精度路径（默认至少 50 位有效数字，最高可超 20 位）。
- 也可以由用户显式指定"计算精度（有效位数）"覆盖自动检测。

说明：
- 高精度路径中，极坐标速度（速率+角度）的三角函数仍使用标准库 math
  （float 精度），角度本身通常只有少量有效位；需要完整精度的用户
  可切换到 X/Y 笛卡尔速度输入。
"""

import json
import math
import re
from decimal import (
    Decimal,
    getcontext,
    ROUND_CEILING,
    ROUND_HALF_EVEN,
)
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Decimal 简写
D = Decimal

# ============================================================
# 科学归一化常量（Decimal 精确版，与 physics.unit_system 保持一致）
# ============================================================
AU = D('1.495978707e11')          # 1 AU = 1.495978707e11 m
SOLAR_MASS = D('1.98892e30')      # 1 M_sun = 1.98892e30 kg
G_SI = D('6.67430e-11')           # m^3 kg^-1 s^-2
DAY = D('86400')
YEAR = D('365.25') * DAY
T0 = (AU ** 3 / (G_SI * SOLAR_MASS)).sqrt()   # 使 G_sim = 1 的标准时间
V0 = AU / T0                                   # 标准速度（m/s）
A0 = AU / T0 ** 2                              # 标准加速度（m/s^2）


def _sig(text: str) -> int:
    """统计数字文本的有效位数（忽略符号、小数点、指数、前导零）。"""
    s = str(text).strip().lower()
    if not s or s in ('0', '-0', '+0'):
        return 1
    if 'e' in s:
        mantissa, _, exp = s.partition('e')
    else:
        mantissa = s
    mantissa = mantissa.lstrip('+-').replace('.', '')
    mantissa = mantissa.lstrip('0')
    return len(mantissa) or 1


def significant_digits(text) -> int:
    """返回数值文本的有效位数（1 ~ 任意）。"""
    return _sig(text)


def float64_exact(text) -> bool:
    """
    判断该数值文本能否被 float64 无损表示。

    若 Decimal(text) == Decimal(repr(float(text)))，说明 float64 往返
    不丢失任何有效位，属于"输入精度较小"的情形。
    """
    try:
        dec = D(str(text).strip())
    except Exception:
        return True
    if not dec.is_finite():
        return True
    try:
        back = D(repr(float(dec)))
    except Exception:
        return True
    return dec == back


def _safe_float_text(text) -> Optional[str]:
    """返回可解析的数值文本；无法解析返回 None。"""
    t = str(text).strip()
    if not t:
        return None
    try:
        float(t)
    except (ValueError, OverflowError):
        return None
    return t


def detect_precision(
    texts: Iterable,
    requested_digits: Optional[int] = None,
) -> Tuple[str, int]:
    """
    检测计算精度。

    Args:
        texts: 所有输入数值的原始文本列表（含位置、速度、质量、半径等）。
        requested_digits: 用户显式指定的有效位数（None = 自动）。

    Returns:
        (mode, digits)
        mode = 'float64' | 'decimal'
        digits = 有效位数（float64 模式固定 16）
    """
    values = [_safe_float_text(t) for t in texts]
    values = [v for v in values if v is not None]

    # 显式指定
    if requested_digits is not None and requested_digits > 0:
        if requested_digits > 15:
            return 'decimal', int(requested_digits)
        return 'float64', 16

    # 自动：任一输入超出 float64 无损表示范围 -> 高精度
    needs = any(not float64_exact(v) for v in values)
    if not needs:
        return 'float64', 16

    max_sig = max((_sig(v) for v in values), default=16)
    digits = max(50, max_sig + 10)
    digits = min(digits, 200)
    return 'decimal', digits


def format_decimal(value, digits: int = 20) -> str:
    """
    将 Decimal 格式化为指定有效位数（科学计数法，指数不补零）。
    """
    if isinstance(value, (int, float)):
        value = D(repr(value)) if isinstance(value, float) else D(value)
    if not isinstance(value, Decimal):
        value = D(str(value))
    if not value.is_finite():
        return str(value)
    if value == 0:
        return '0'
    digits = max(1, int(digits))
    text = format(value, f'.{digits - 1}e')
    return _normalize_exponent(text)


def _normalize_exponent(text: str) -> str:
    """将 e-07 规范为 e-7、e+30 规范为 e30。"""
    low = text.lower()
    if 'e' not in low:
        return text
    mantissa, _, exp = low.partition('e')
    return f"{mantissa}e{int(exp)}"


# ============================================================
# 高精度单位换算（科学模式：现实单位 -> 归一化模拟单位）
# 与 physics.unit_system.UnitSystem 语义一致，但使用 Decimal。
# ============================================================

# 长度: 1 单位 -> 米
_LEN_SI = {'m': D(1), 'km': D('1e3'), 'au': AU}
# 质量: 1 单位 -> 千克
_MASS_SI = {'kg': D(1), 'm_sun': SOLAR_MASS}
# 时间: 1 单位 -> 秒
_TIME_SI = {'s': D(1), 'day': DAY, 'year': YEAR}
# 速度: 1 单位 -> 米/秒
_VEL_SI = {'m/s': D(1), 'km/s': D('1e3'), 'au/t0': V0}


def _normalize_unit_key(unit) -> str:
    """规范化单位字符串（小写、去空格/上标）。"""
    if unit is None:
        return ''
    s = str(unit).strip().lower().replace('²', '2').replace('^', '').replace(' ', '')
    alias = {
        'msun': 'm_sun', 'solar_mass': 'm_sun', 'solar_masses': 'm_sun',
        'sec': 's', 'second': 's', 'seconds': 's',
        'days': 'day', 'years': 'year', 'yr': 'year',
        'au/t0': 'au/t0', 'du/tu': 'du/tu',
    }
    return alias.get(s, s)


def to_simulation_decimal(value, unit: str, is_simulation_mode: bool) -> Decimal:
    """
    将（科学模式）现实单位数值转换为归一化模拟单位（Decimal）。

    模拟模式直接原样返回；科学模式按 UnitSystem 相同规则换算。
    """
    v = value if isinstance(value, Decimal) else D(str(value))
    if is_simulation_mode:
        return v
    key = _normalize_unit_key(unit)
    if key in ('du', 'mu', 'tu', 'du/tu'):
        return v
    if key in _LEN_SI:
        return v * _LEN_SI[key] / AU
    if key in _MASS_SI:
        return v * _MASS_SI[key] / SOLAR_MASS
    if key in _TIME_SI:
        return v * _TIME_SI[key] / T0
    if key in _VEL_SI:
        return v * _VEL_SI[key] / V0
    # 未知单位：按模拟单位处理
    return v


def velocity_from_polar(speed, angle_deg, unit: str, is_simulation_mode: bool) -> Tuple[Decimal, Decimal]:
    """
    极坐标速度 -> 笛卡尔速度（Decimal）。

    三角函数使用标准库 math（float 精度），结果转为 Decimal。
    """
    speed_sim = to_simulation_decimal(speed, unit, is_simulation_mode)
    theta = math.radians(float(angle_deg))
    return speed_sim * D(repr(math.cos(theta))), speed_sim * D(repr(math.sin(theta)))


def load_scene_preserving_precision(path) -> dict:
    """
    读取 Scene JSON，所有数值保持为 Decimal（不损失输入精度）。

    用于"导入预设"：若预设内数值位数超出 float64，自动启用高精度计算。
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f, parse_float=D, parse_int=D)


def count_steps(duration, dt) -> int:
    """
    计算所需模拟步数 = ceil(duration / dt)。

    使用 Decimal 避免浮点除法的舍入误差（例如 100 / 1e-7）。
    """
    d_dur = duration if isinstance(duration, Decimal) else D(str(duration))
    d_dt = dt if isinstance(dt, Decimal) else D(str(dt))
    if d_dt <= 0 or d_dur <= 0:
        return 0
    q = d_dur / d_dt
    return int(q.to_integral_value(rounding=ROUND_CEILING))
