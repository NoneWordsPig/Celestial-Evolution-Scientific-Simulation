"""
Physics 物理引擎模块

提供天体引力模拟的核心物理计算功能。

所有物理量均使用模拟单位（Simulation Units）：
    G  = 1（无量纲）
    MU = 1（质量单位）
    DU = 1（距离单位）
    TU = 1（时间单位，由 G, MU, DU 导出）

主要组件：
- Body: 天体数据类（physical_radius / render_radius 分离）
- GravitySolver: 万有引力计算
- CollisionHandler: 碰撞检测与融合
- VelocityVerletIntegrator / RK4Integrator: 数值积分器
- PhysicsEngine: 物理引擎主循环
- Mode: 模拟模式枚举（SIMULATION / SCIENTIFIC）
- SimulationFormatter / ScientificFormatter: 单位格式化器
- UnitSystem: 模拟单位系统
- UnitConverter: 现实单位转换器
- ReferenceFrame: 质心参考系管理
- TransitionManager: 过渡动画管理
"""

from .body import Body
from .gravity import GravitySolver
from .gravity_opt import GravitySolverOpt
from .integrator_opt import RK4IntegratorOpt
from .performance_monitor import PerformanceMonitor
from .collision import CollisionHandler
from .integrator import VelocityVerletIntegrator, RK4Integrator, IntegratorFactory
from .engine import PhysicsEngine
from .mode import Mode
from .formatter import SimulationFormatter, ScientificFormatter
from .units import UnitSystem, UnitConverter, DEFAULT_UNITS
from .camera import Camera
from .scale_bar import ScaleBar, compute_nice_number
from .reference_frame import ReferenceFrame
from .transitions import (
    Transition,
    CameraTransition,
    MomentumCorrectionTransition,
    TransitionManager,
    ease_in_out_cubic,
    lerp,
)
from .constants import (
    G, SOFTENING, DEFAULT_DT, MAX_TRAJECTORY_LENGTH,
    COLLISION_FACTOR, RADIUS_MERGE_EXPONENT,
    DEFAULT_VIEW_X_RANGE, DEFAULT_VIEW_Y_RANGE,
    DEFAULT_CENTRAL_STAR_MASS, DEFAULT_PLANET_MASS,
    DEFAULT_ORBIT_DISTANCE, DEFAULT_ORBITAL_VELOCITY,
)

__all__ = [
    # 核心类
    'Body',
    'GravitySolver',
'GravitySolverOpt',
'RK4IntegratorOpt',
'PerformanceMonitor',
    'CollisionHandler',
    'VelocityVerletIntegrator',
    'RK4Integrator',
    'IntegratorFactory',
    'PhysicsEngine',
    # 模式
    'Mode',
    # 格式化器
    'SimulationFormatter',
    'ScientificFormatter',
    # 单位系统
    'UnitSystem',
    'UnitConverter',
    'DEFAULT_UNITS',
    # 摄像机和比例尺
    'Camera',
    'ScaleBar',
    'compute_nice_number',
    # 参考系和过渡
    'ReferenceFrame',
    'Transition',
    'CameraTransition',
    'MomentumCorrectionTransition',
    'TransitionManager',
    'ease_in_out_cubic',
    'lerp',
    # 物理常量
    'G',
    'SOFTENING',
    'DEFAULT_DT',
    'MAX_TRAJECTORY_LENGTH',
    'COLLISION_FACTOR',
    'RADIUS_MERGE_EXPONENT',
    # 默认视觉尺度
    'DEFAULT_VIEW_X_RANGE',
    'DEFAULT_VIEW_Y_RANGE',
    'DEFAULT_CENTRAL_STAR_MASS',
    'DEFAULT_PLANET_MASS',
    'DEFAULT_ORBIT_DISTANCE',
    'DEFAULT_ORBITAL_VELOCITY',
]


