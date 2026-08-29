"""
Scientific 科学计算模块

提供：
- precision: 高精度数值解析、精度检测、Decimal 单位换算
- simulator: 批量离线 N 体模拟（float64 快速路径 + Decimal 高精度路径）
- worker: Qt 后台线程封装
"""

from .precision import (
    D,
    detect_precision,
    significant_digits,
    float64_exact,
    format_decimal,
    load_scene_preserving_precision,
)
from .simulator import (
    SimulationConfig,
    SimulationResult,
    build_state_from_scene,
    run_simulation,
)

__all__ = [
    'D',
    'detect_precision',
    'significant_digits',
    'float64_exact',
    'format_decimal',
    'load_scene_preserving_precision',
    'SimulationConfig',
    'SimulationResult',
    'build_state_from_scene',
    'run_simulation',
]
