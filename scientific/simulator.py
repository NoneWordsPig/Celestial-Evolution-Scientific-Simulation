"""
批量离线 N 体模拟器

实现"科学模拟"核心流程：
1. 按固定时间步长 dt 直接进行 N 体计算（不渲染），期间只保留当前时刻
   每个星体的位置/速度用于下一步计算；
2. 仅在"渲染帧"（每 playback_speed / 60 时间单位一帧）记录星体位置等快照，
   供模拟完成后按 60 FPS 回放；
3. 显示"模拟进度"。

两条计算路径：
- float64 快速路径：NumPy 向量化 RK4（与 physics.integrator_opt.RK4IntegratorOpt
  使用完全相同的 RK4 格式），适用于"输入精度较小"的常规情形；
- decimal 高精度路径：Decimal RK4（纯 Python），支持 20 位以上有效数字，
  当输入精度超出 float64 无损表示范围或用户显式指定高精度时启用。

碰撞融合：浮点路径复用 physics.collision.CollisionHandler；
Decimal 路径实现等价的动量/质量守恒融合。
"""

import math
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

import numpy as np

from physics import Body, CollisionHandler
from physics.constants import G, COLLISION_FACTOR, SOFTENING

from .precision import (
    D,
    count_steps,
    to_simulation_decimal,
    velocity_from_polar,
)

ProgressFn = Optional[Callable[[int, str], None]]
CancelFn = Optional[Callable[[], bool]]


# ============================================================
# 配置与结果
# ============================================================

@dataclass
class SimulationConfig:
    """科学模拟配置"""
    duration: float          # 模拟时长（TU）
    dt: float                # 模拟时间步长（TU）
    playback_speed: float    # 播放速度：每秒渲染的标准时间数
    requested_digits: Optional[int] = None  # 显式计算精度（有效位数），None=自动
    frame_rate: float = 60.0                # 回放帧率（帧/秒）
    softening: float = SOFTENING


@dataclass
class SimulationResult:
    """模拟结果：渲染帧快照 + 元信息"""
    config: SimulationConfig
    precision_mode: str          # 'float64' | 'decimal'
    precision_digits: int
    total_steps: int
    elapsed_seconds: float
    integrator: str = 'rk4'
    cancelled: bool = False
    frame_times: List[float] = field(default_factory=list)
    frame_positions: List = field(default_factory=list)    # [frame][body][x, y]
    frame_velocities: List = field(default_factory=list)   # [frame][body][vx, vy]
    frame_masses: List = field(default_factory=list)       # [frame][body]
    frame_radii: List = field(default_factory=list)        # [frame][body]
    frame_names: List = field(default_factory=list)        # [frame][body]
    frame_colors: List = field(default_factory=list)       # [frame][body]

    @property
    def frame_count(self) -> int:
        return len(self.frame_times)

    @property
    def body_count(self) -> int:
        return len(self.frame_names[0]) if self.frame_names else 0


@dataclass
class InitialState:
    """初始状态（同时携带 float64 与原始高精度输入）"""
    bodies: List[Body]                 # float64 表示（始终可用）
    input_texts: List[str]             # 所有数值原始文本（用于精度检测）
    scene: Optional[dict] = None       # 预设原始 dict（Decimal 数值）
    entries: Optional[List[dict]] = None  # 新设置原始输入（Decimal 文本）


# ============================================================
# 初始状态构建
# ============================================================

def build_state_from_scene(scene: dict, ) -> InitialState:
    """从预设 Scene dict（可能含 Decimal）构建初始状态。"""
    bodies = []
    texts = []
    for b in scene.get('bodies', []):
        pos = b.get('position', [0, 0])
        vel = b.get('velocity', [0, 0])
        bodies.append(Body(
            name=b.get('name', 'Body'),
            mass=float(b.get('mass', 1.0)),
            physical_radius=float(b.get('radius', 1.0)),
            position=(float(pos[0]), float(pos[1])),
            velocity=(float(vel[0]), float(vel[1])),
            color=_scene_color(b),
        ))
        for v in (*pos, *vel, b.get('mass', 1.0), b.get('radius', 1.0)):
            texts.append(str(v))
    return InitialState(bodies=bodies, input_texts=texts, scene=scene)


def _scene_color(b: dict) -> Tuple[float, float, float]:
    color = b.get('color')
    if color is not None:
        try:
            return (float(color[0]), float(color[1]), float(color[2]))
        except (TypeError, ValueError, IndexError):
            pass
    return (1.0, 1.0, 1.0)


def build_state_from_entries(bodies: List[Body], entries: Optional[List[dict]]) -> InitialState:
    """从新设置输入（Body + 原始文本）构建初始状态。"""
    texts = []
    for e in (entries or []):
        texts.extend(_entry_texts(e))
    if not texts:
        for b in bodies:
            for v in (b.position[0], b.position[1], b.velocity[0], b.velocity[1], b.mass, b.physical_radius):
                texts.append(repr(v))
    return InitialState(bodies=bodies, input_texts=texts, entries=entries)


def _entry_texts(e: dict) -> List[str]:
    texts = [e.get('mass', '1'), e.get('radius', '1e-4'),
             e.get('pos_x', '0'), e.get('pos_y', '0')]
    v = e.get('velocity', {})
    if v.get('mode') == 'cartesian':
        texts += [v.get('vx', '0'), v.get('vy', '0')]
    else:
        texts += [v.get('speed', '0'), v.get('angle', '0')]
    return texts


# ============================================================
# 模拟入口
# ============================================================

def run_simulation(
    initial: InitialState,
    config: SimulationConfig,
    progress: ProgressFn = None,
    cancel: CancelFn = None,
) -> Optional[SimulationResult]:
    """
    运行科学模拟。

    Returns:
        SimulationResult；被取消时返回 None。
    """
    from .precision import detect_precision
    mode, digits = detect_precision(initial.input_texts, config.requested_digits)

    if mode == 'float64':
        state = _float_state(initial.bodies)
        return _run_float64(state, initial, config, progress, cancel)
    else:
        from decimal import getcontext
        # 额外 8 位保护位，避免中间运算舍入损失
        getcontext().prec = digits + 8
        state = _decimal_state(initial)
        return _run_decimal(state, initial, config, digits, progress, cancel)


# ============================================================
# float64 路径
# ============================================================

class _FloatState:
    __slots__ = ('names', 'colors', 'masses', 'radii', 'positions', 'velocities')

    def __init__(self, names, colors, masses, radii, positions, velocities):
        self.names = names
        self.colors = colors
        self.masses = masses
        self.radii = radii
        self.positions = positions
        self.velocities = velocities


def _float_state(bodies: List[Body]) -> _FloatState:
    n = len(bodies)
    return _FloatState(
        names=[b.name for b in bodies],
        colors=[tuple(float(c) for c in b.color) for b in bodies],
        masses=np.array([b.mass for b in bodies], dtype=np.float64),
        radii=np.array([b.physical_radius for b in bodies], dtype=np.float64),
        positions=np.array([b.position for b in bodies], dtype=np.float64).reshape(n, 2),
        velocities=np.array([b.velocity for b in bodies], dtype=np.float64).reshape(n, 2),
    )


def _acc_float(pos, mass, softening_sq: float) -> np.ndarray:
    """NumPy 向量化引力加速度（与 GravitySolver 相同公式）。"""
    n = pos.shape[0]
    if n == 0:
        return np.zeros((0, 2), dtype=np.float64)
    if n == 1:
        return np.zeros((1, 2), dtype=np.float64)
    diff = pos[np.newaxis, :, :] - pos[:, np.newaxis, :]        # (n,n,2)
    dist_sq = diff[..., 0] ** 2 + diff[..., 1] ** 2 + softening_sq
    idx = np.arange(n)
    dist_sq[idx, idx] = 1.0
    inv_cube = dist_sq ** -1.5
    inv_cube[idx, idx] = 0.0
    weights = mass[np.newaxis, :] * inv_cube                    # (n,n)
    acc = (weights[:, :, np.newaxis] * diff).sum(axis=1) * G
    return acc


def _rk4_step_float(pos, vel, mass, dt, softening_sq):
    """与 RK4IntegratorOpt 完全相同的 RK4 步进。"""
    n = pos.shape[0]
    if n == 0:
        return pos, vel
    half = 0.5 * dt
    sixth = dt / 6.0

    a1 = _acc_float(pos, mass, softening_sq)
    v1 = vel.copy()

    p2 = pos + half * v1
    v2 = vel + half * a1
    a2 = _acc_float(p2, mass, softening_sq)

    p3 = pos + half * v2
    v3 = vel + half * a2
    a3 = _acc_float(p3, mass, softening_sq)

    p4 = pos + dt * v3
    v4 = vel + dt * a3
    a4 = _acc_float(p4, mass, softening_sq)

    new_pos = pos + sixth * (v1 + 2.0 * v2 + 2.0 * v3 + v4)
    new_vel = vel + sixth * (a1 + 2.0 * a2 + 2.0 * a3 + a4)
    return new_pos, new_vel


def _collision_exists_float(pos, radii, factor=COLLISION_FACTOR) -> bool:
    n = pos.shape[0]
    if n < 2:
        return False
    diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
    dist_sq = diff[..., 0] ** 2 + diff[..., 1] ** 2
    th = (radii[:, np.newaxis] + radii[np.newaxis, :]) * factor
    th_sq = th * th
    iu = np.triu_indices(n, 1)
    return bool(np.any(dist_sq[iu] < th_sq[iu]))


def _resolve_collisions_float(state: _FloatState) -> None:
    """将数组状态转成 Body 列表，复用 CollisionHandler 融合后写回。"""
    n = state.positions.shape[0]
    bodies = [
        Body(
            name=state.names[i],
            mass=float(state.masses[i]),
            physical_radius=float(state.radii[i]),
            position=(float(state.positions[i, 0]), float(state.positions[i, 1])),
            velocity=(float(state.velocities[i, 0]), float(state.velocities[i, 1])),
            color=state.colors[i],
        )
        for i in range(n)
    ]
    merged = CollisionHandler().resolve_collisions(bodies)
    m = len(merged)
    state.names = [b.name for b in merged]
    state.colors = [tuple(float(c) for c in b.color) for b in merged]
    state.masses = np.array([b.mass for b in merged], dtype=np.float64)
    state.radii = np.array([b.physical_radius for b in merged], dtype=np.float64)
    state.positions = np.array([b.position for b in merged], dtype=np.float64).reshape(m, 2)
    state.velocities = np.array([b.velocity for b in merged], dtype=np.float64).reshape(m, 2)


def _run_float64(state: _FloatState, initial, config, progress, cancel) -> Optional[SimulationResult]:
    result = SimulationResult(
        config=config,
        precision_mode='float64',
        precision_digits=16,
        total_steps=0,
        elapsed_seconds=0.0,
    )
    pos = state.positions.copy()
    vel = state.velocities.copy()
    mass = state.masses.copy()
    radii = state.radii.copy()
    names = list(state.names)
    colors = list(state.colors)

    dt = float(config.dt)
    if dt <= 0:
        raise ValueError("模拟时间步长必须大于 0")
    duration = float(config.duration)
    if duration <= 0:
        raise ValueError("模拟时长必须大于 0")
    speed = float(config.playback_speed)
    if speed <= 0:
        raise ValueError("播放速度必须大于 0")

    total_steps = count_steps(config.duration, config.dt)
    result.total_steps = total_steps
    frame_dt = speed / config.frame_rate
    softening_sq = float(config.softening) ** 2

    t0_wall = time.perf_counter()
    last_report = t0_wall

    def record(t, p, v, m, r, nm, cl):
        result.frame_times.append(float(t))
        result.frame_positions.append(p.copy().tolist())
        result.frame_velocities.append(v.copy().tolist())
        result.frame_masses.append(m.tolist())
        result.frame_radii.append(r.tolist())
        result.frame_names.append(list(nm))
        result.frame_colors.append(list(cl))

    def emit(step: int, force: bool = False):
        nonlocal last_report
        if progress is None:
            return
        now = time.perf_counter()
        if not force and now - last_report < 0.05:
            return
        last_report = now
        percent = int(step * 100.0 / total_steps) if total_steps else 100
        elapsed = now - t0_wall
        eta = elapsed * (total_steps - step) / max(step, 1) if step > 0 else 0.0
        progress(min(percent, 100), f"已计算 {step:,}/{total_steps:,} 步 · 已用 {elapsed:.1f}s · 预计剩余 {eta:.1f}s")

    # 初始帧 t=0
    record(0.0, pos, vel, mass, radii, names, colors)
    next_frame_time = frame_dt

    sim_time = 0.0
    step = 0
    eps = dt * 1e-9
    while sim_time < duration - eps and step < total_steps:
        if cancel is not None and cancel():
            result.cancelled = True
            return None
        dt_eff = min(dt, duration - sim_time)
        pos, vel = _rk4_step_float(pos, vel, mass, dt_eff, softening_sq)
        sim_time += dt_eff

        # 碰撞检测与融合（与原始引擎一致，每步执行）
        if _collision_exists_float(pos, radii):
            state.positions = pos
            state.velocities = vel
            state.masses = mass
            state.radii = radii
            state.names = names
            state.colors = colors
            _resolve_collisions_float(state)
            pos, vel, mass, radii = state.positions, state.velocities, state.masses, state.radii
            names, colors = state.names, state.colors

        # 记录经过的渲染帧
        while next_frame_time <= sim_time + eps:
            record(next_frame_time, pos, vel, mass, radii, names, colors)
            next_frame_time += frame_dt

        step += 1
        emit(step)

    # 确保最后一帧覆盖到模拟时长
    if not result.frame_times or result.frame_times[-1] < duration - eps:
        record(duration, pos, vel, mass, radii, names, colors)

    result.elapsed_seconds = time.perf_counter() - t0_wall
    if progress is not None:
        progress(100, f"模拟完成 · 共 {total_steps:,} 步 · {len(result.frame_times):,} 个渲染帧 · 耗时 {result.elapsed_seconds:.1f}s")
    return result


# ============================================================
# Decimal 高精度路径
# ============================================================

class _DecimalState:
    __slots__ = ('names', 'colors', 'masses', 'radii', 'positions', 'velocities')

    def __init__(self, names, colors, masses, radii, positions, velocities):
        self.names = names
        self.colors = colors
        self.masses = masses
        self.radii = radii
        self.positions = positions
        self.velocities = velocities


def _d(value) -> D:
    return value if isinstance(value, D) else D(str(value))


def _decimal_state(initial: InitialState) -> _DecimalState:
    if initial.scene is not None:
        return _decimal_state_from_scene(initial.scene)
    if initial.entries is not None:
        return _decimal_state_from_entries(initial.entries, initial.bodies)
    return _decimal_state_from_bodies(initial.bodies)


def _decimal_state_from_scene(scene: dict) -> _DecimalState:
    names, colors, masses, radii, positions, velocities = [], [], [], [], [], []
    for b in scene.get('bodies', []):
        names.append(b.get('name', 'Body'))
        colors.append(_scene_color(b))
        masses.append(max(_d(b.get('mass', 1)), D('1e-10')))
        radii.append(max(_d(b.get('radius', 1)), D('1e-10')))
        pos = b.get('position', [0, 0])
        vel = b.get('velocity', [0, 0])
        positions.append([_d(pos[0]), _d(pos[1])])
        velocities.append([_d(vel[0]), _d(vel[1])])
    return _DecimalState(names, colors, masses, radii, positions, velocities)


def _decimal_state_from_entries(entries: List[dict], bodies: List[Body]) -> _DecimalState:
    names, colors, masses, radii, positions, velocities = [], [], [], [], [], []
    for i, e in enumerate(entries):
        is_sci = bool(e.get('is_scientific', False))
        names.append(e.get('name') or (bodies[i].name if i < len(bodies) else f"Body {i+1}"))
        colors.append(tuple(float(c) for c in e.get('color', (1.0, 1.0, 1.0))))
        masses.append(max(to_simulation_decimal(e.get('mass', '1'), e.get('mass_unit', ''), not is_sci), D('1e-10')))
        radii.append(max(to_simulation_decimal(e.get('radius', '1e-4'), e.get('radius_unit', ''), not is_sci), D('1e-10')))
        px = to_simulation_decimal(e.get('pos_x', '0'), e.get('pos_x_unit', ''), not is_sci)
        py = to_simulation_decimal(e.get('pos_y', '0'), e.get('pos_y_unit', ''), not is_sci)
        positions.append([px, py])
        v = e.get('velocity', {})
        if v.get('mode') == 'cartesian':
            vx = to_simulation_decimal(v.get('vx', '0'), v.get('vx_unit', ''), not is_sci)
            vy = to_simulation_decimal(v.get('vy', '0'), v.get('vy_unit', ''), not is_sci)
        else:
            vx, vy = velocity_from_polar(v.get('speed', '0'), v.get('angle', '0'),
                                         v.get('speed_unit', ''), not is_sci)
        velocities.append([vx, vy])
    return _DecimalState(names, colors, masses, radii, positions, velocities)


def _decimal_state_from_bodies(bodies: List[Body]) -> _DecimalState:
    names, colors, masses, radii, positions, velocities = [], [], [], [], [], []
    for b in bodies:
        names.append(b.name)
        colors.append(tuple(float(c) for c in b.color))
        masses.append(max(_d(repr(b.mass)), D('1e-10')))
        radii.append(max(_d(repr(b.physical_radius)), D('1e-10')))
        positions.append([_d(repr(b.position[0])), _d(repr(b.position[1]))])
        velocities.append([_d(repr(b.velocity[0])), _d(repr(b.velocity[1]))])
    return _DecimalState(names, colors, masses, radii, positions, velocities)


def _acc_decimal(pos, mass, softening_sq: D) -> List[List[D]]:
    n = len(pos)
    acc = [[D(0), D(0)] for _ in range(n)]
    G_dec = D(str(G))
    for i in range(n):
        ai = acc[i]
        xi, yi = pos[i]
        for j in range(n):
            if i == j:
                continue
            dx = pos[j][0] - xi
            dy = pos[j][1] - yi
            dsq = dx * dx + dy * dy + softening_sq
            d = dsq.sqrt()
            factor = G_dec * mass[j] / (dsq * d)
            ai[0] += factor * dx
            ai[1] += factor * dy
    return acc


def _rk4_step_decimal(pos, vel, mass, dt: D, softening_sq: D):
    n = len(pos)
    if n == 0:
        return pos, vel
    half = dt / 2
    sixth = dt / 6

    a1 = _acc_decimal(pos, mass, softening_sq)
    v1 = [row[:] for row in vel]

    p2 = [[pos[i][0] + half * v1[i][0], pos[i][1] + half * v1[i][1]] for i in range(n)]
    v2 = [[vel[i][0] + half * a1[i][0], vel[i][1] + half * a1[i][1]] for i in range(n)]
    a2 = _acc_decimal(p2, mass, softening_sq)

    p3 = [[pos[i][0] + half * v2[i][0], pos[i][1] + half * v2[i][1]] for i in range(n)]
    v3 = [[vel[i][0] + half * a2[i][0], vel[i][1] + half * a2[i][1]] for i in range(n)]
    a3 = _acc_decimal(p3, mass, softening_sq)

    p4 = [[pos[i][0] + dt * v3[i][0], pos[i][1] + dt * v3[i][1]] for i in range(n)]
    v4 = [[vel[i][0] + dt * a3[i][0], vel[i][1] + dt * a3[i][1]] for i in range(n)]
    a4 = _acc_decimal(p4, mass, softening_sq)

    new_pos = [
        [pos[i][0] + sixth * (v1[i][0] + 2 * v2[i][0] + 2 * v3[i][0] + v4[i][0]),
         pos[i][1] + sixth * (v1[i][1] + 2 * v2[i][1] + 2 * v3[i][1] + v4[i][1])]
        for i in range(n)
    ]
    new_vel = [
        [vel[i][0] + sixth * (a1[i][0] + 2 * a2[i][0] + 2 * a3[i][0] + a4[i][0]),
         vel[i][1] + sixth * (a1[i][1] + 2 * a2[i][1] + 2 * a3[i][1] + a4[i][1])]
        for i in range(n)
    ]
    return new_pos, new_vel


def _collision_exists_decimal(pos, radii, factor=COLLISION_FACTOR) -> bool:
    n = len(pos)
    f = D(str(factor))
    for i in range(n):
        for j in range(i + 1, n):
            dx = pos[i][0] - pos[j][0]
            dy = pos[i][1] - pos[j][1]
            dsq = dx * dx + dy * dy
            th = (radii[i] + radii[j]) * f
            if dsq < th * th:
                return True
    return False


def _resolve_collisions_decimal(state: _DecimalState) -> None:
    """贪心合并所有碰撞对（与 CollisionHandler 相同策略），直到无碰撞。"""
    names = list(state.names)
    colors = [list(c) for c in state.colors]
    masses = list(state.masses)
    radii = list(state.radii)
    pos = [row[:] for row in state.positions]
    vel = [row[:] for row in state.velocities]
    factor = D(str(COLLISION_FACTOR))

    while True:
        n = len(pos)
        pair = None
        for i in range(n):
            for j in range(i + 1, n):
                dx = pos[i][0] - pos[j][0]
                dy = pos[i][1] - pos[j][1]
                dsq = dx * dx + dy * dy
                th = (radii[i] + radii[j]) * factor
                if dsq < th * th:
                    pair = (i, j)
                    break
            if pair is not None:
                break
        if pair is None:
            break
        i, j = pair
        if i > j:
            i, j = j, i
        m_new = masses[i] + masses[j]
        p_new = [
            (masses[i] * pos[i][0] + masses[j] * pos[j][0]) / m_new,
            (masses[i] * pos[i][1] + masses[j] * pos[j][1]) / m_new,
        ]
        v_new = [
            (masses[i] * vel[i][0] + masses[j] * vel[j][0]) / m_new,
            (masses[i] * vel[i][1] + masses[j] * vel[j][1]) / m_new,
        ]
        r_new = (radii[i] ** 3 + radii[j] ** 3) ** (D(1) / D(3))
        name_new = f"{names[i]}+{names[j]}" if names[i] and names[j] else (names[i] or names[j])
        c_new = [
            (masses[i] * colors[i][k] + masses[j] * colors[j][k]) / m_new
            for k in range(3)
        ]
        # 移除 j 后放回 i（保证索引稳定）
        for lst in (pos, vel, masses, radii, names, colors):
            lst.pop(j)
        pos[i], vel[i], masses[i], radii[i], names[i], colors[i] = p_new, v_new, m_new, r_new, name_new, c_new

    state.positions = pos
    state.velocities = vel
    state.masses = masses
    state.radii = radii
    state.names = names
    state.colors = [tuple(float(c) for c in row) for row in colors]


def _run_decimal(state: _DecimalState, initial, config, digits, progress, cancel) -> Optional[SimulationResult]:
    result = SimulationResult(
        config=config,
        precision_mode='decimal',
        precision_digits=digits,
        total_steps=0,
        elapsed_seconds=0.0,
    )
    pos = [row[:] for row in state.positions]
    vel = [row[:] for row in state.velocities]
    mass = list(state.masses)
    radii = list(state.radii)
    names = list(state.names)
    colors = list(state.colors)

    dt = _d(config.dt)
    if dt <= 0:
        raise ValueError("模拟时间步长必须大于 0")
    duration = _d(config.duration)
    if duration <= 0:
        raise ValueError("模拟时长必须大于 0")
    speed = _d(config.playback_speed)
    if speed <= 0:
        raise ValueError("播放速度必须大于 0")

    total_steps = count_steps(config.duration, config.dt)
    result.total_steps = total_steps
    frame_dt = speed / _d(str(config.frame_rate))
    softening_sq = _d(str(config.softening)) ** 2

    t0_wall = time.perf_counter()
    last_report = t0_wall

    def record(t, p, v, m, r, nm, cl):
        result.frame_times.append(float(t))
        result.frame_positions.append([row[:] for row in p])
        result.frame_velocities.append([row[:] for row in v])
        result.frame_masses.append(list(m))
        result.frame_radii.append(list(r))
        result.frame_names.append(list(nm))
        result.frame_colors.append(list(cl))

    def emit(step: int, force: bool = False):
        nonlocal last_report
        if progress is None:
            return
        now = time.perf_counter()
        if not force and now - last_report < 0.1:
            return
        last_report = now
        percent = int(step * 100.0 / total_steps) if total_steps else 100
        elapsed = now - t0_wall
        eta = elapsed * (total_steps - step) / max(step, 1) if step > 0 else 0.0
        progress(min(percent, 100), f"高精度({digits}位) · 已计算 {step:,}/{total_steps:,} 步 · 已用 {elapsed:.1f}s · 预计剩余 {eta:.1f}s")

    record(D(0), pos, vel, mass, radii, names, colors)
    next_frame_time = frame_dt
    sim_time = D(0)
    eps = dt / D('1e9')
    step = 0
    while sim_time < duration - eps and step < total_steps:
        if cancel is not None and cancel():
            result.cancelled = True
            return None
        dt_eff = min(dt, duration - sim_time)
        pos, vel = _rk4_step_decimal(pos, vel, mass, dt_eff, softening_sq)
        sim_time += dt_eff

        if _collision_exists_decimal(pos, radii):
            state.positions = pos
            state.velocities = vel
            state.masses = mass
            state.radii = radii
            state.names = names
            state.colors = colors
            _resolve_collisions_decimal(state)
            pos, vel, mass, radii = state.positions, state.velocities, state.masses, state.radii
            names, colors = state.names, state.colors

        while next_frame_time <= sim_time + eps:
            record(next_frame_time, pos, vel, mass, radii, names, colors)
            next_frame_time += frame_dt

        step += 1
        emit(step)

    if not result.frame_times or result.frame_times[-1] < float(duration) - 1e-12:
        record(duration, pos, vel, mass, radii, names, colors)

    result.elapsed_seconds = time.perf_counter() - t0_wall
    if progress is not None:
        progress(100, f"模拟完成 · 共 {total_steps:,} 步 · {len(result.frame_times):,} 个渲染帧 · 耗时 {result.elapsed_seconds:.1f}s")
    return result

