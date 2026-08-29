"""
物理引擎主循环模块

协调引力计算、积分、碰撞检测等步骤
管理世界状态和时间推进
"""

from collections import deque

import time
import numpy as np
from typing import List, Optional
from .body import Body
from .gravity import GravitySolver
from .gravity_opt import GravitySolverOpt
from .integrator_opt import RK4IntegratorOpt
from .collision import CollisionHandler
from .integrator import VelocityVerletIntegrator, RK4Integrator, IntegratorFactory
from .constants import (
    G, SOFTENING, DEFAULT_DT, MAX_TRAJECTORY_LENGTH,
    BASE_SIMULATION_RATE, MAX_SUBSTEPS_PER_FRAME,
)


class PhysicsEngine:
    """
    物理引擎
    
    管理整个模拟的生命周期：
    1. 引力计算
    2. 数值积分（更新位置和速度）
    3. 碰撞检测与融合
    4. 轨迹记录
    5. 统计量计算（质心、能量等）
    """
    
    def __init__(
        self,
        integrator_type: str = 'verlet',
        softening: float = SOFTENING,
        dt: float = DEFAULT_DT,
        time_scale: float = 1.0,
        use_optimized: bool = True,
        use_gpu: bool = True,
        n_workers: int = None
    ):
        """
        初始化物理引擎
        
        Args:
            integrator_type: 积分器类型 ('verlet' 或 'rk4')
            softening: 软化因子
            dt: 基础时间步长
            time_scale: 时间倍率（1.0 = 正常速度）
        """
                # 物理组件
        if use_optimized:
            self.gravity_solver = GravitySolverOpt(
                softening=softening, 
                use_gpu=use_gpu, 
                )
            if integrator_type == 'rk4':
                self.integrator = RK4IntegratorOpt(self.gravity_solver)
            else:
                self.integrator = IntegratorFactory.create(integrator_type, self.gravity_solver)
        else:
            self.gravity_solver = GravitySolver(softening=softening)
            self.integrator = IntegratorFactory.create(integrator_type, self.gravity_solver)
        self.collision_handler = CollisionHandler()
        # 可选计时钩子（None = 关闭，无额外开销）；不参与任何数值计算
        self._timing = None
        
        # 世界状态
        self.bodies: List[Body] = []
        self.simulation_time: float = 0.0  # 模拟时间
        
        # 全局轨迹历史（所有天体的轨迹点，deque 自动截断）
        self.trajectory_history = deque(maxlen=MAX_TRAJECTORY_LENGTH)
        
        # 时间控制
        self.dt = dt
        self._accumulator = 0.0  # 平滑步进余数（TU）
        self.time_scale = time_scale  # 属性 setter 同步 simulation_rate
        
        # Velocity Verlet 需要的上一步加速度缓存
        self._cached_accelerations: Optional[np.ndarray] = None
        # 诊断标志：上一次 advance 是否因单帧子步上限被截断（供 UI 检测“倍率已达上限”）
        self.last_advance_capped = False
    
    def add_body(self, body: Body) -> None:
        """
        添加天体到模拟中
        
        Args:
            body: 要添加的天体
        """
        self.bodies.append(body)
        # 添加天体后，加速度缓存失效
        self._cached_accelerations = None
    
    def remove_body(self, index: int) -> Body:
        """
        移除指定索引的天体
        
        Args:
            index: 天体索引
            
        Returns:
            被移除的天体
        """
        body = self.bodies.pop(index)
        self._cached_accelerations = None
        return body
    
    def clear(self) -> None:
        """清空所有天体和轨迹"""
        self.bodies.clear()
        self.trajectory_history.clear()
        self._accumulator = 0.0
        self.simulation_time = 0.0
        self._cached_accelerations = None

    @property
    def time_scale(self) -> float:
        """时间倍率（1× = BASE_SIMULATION_RATE TU/s，即旧版 5×）"""
        return self._time_scale

    @time_scale.setter
    def time_scale(self, value: float):
        self._time_scale = float(value)
        # 目标推进速率（TU/s），与 dt 解耦；数值精度由固定 dt 保证
        self.simulation_rate = BASE_SIMULATION_RATE * self._time_scale
    
    def step(self) -> None:
        """
        执行一步物理模拟
        
        包含：
        1. 根据 time_scale 确定子步数
        2. 对每个子步执行：积分 -> 碰撞 -> 轨迹记录
        """
        # 计算每帧需要执行的物理子步数
        updates_per_frame = int(self.time_scale)
        fractional_part = self.time_scale - updates_per_frame
        
        # 执行整数部分
        for _ in range(updates_per_frame):
            self._single_step()
        
        # 小数部分用概率补偿
        if np.random.random() < fractional_part:
            self._single_step()

    def advance(self, wall_seconds: float) -> int:
        """
        按墙钟时间推进模拟（fixed timestep + accumulator）。

        目标速率 = BASE_SIMULATION_RATE × time_scale（TU/s）；
        每帧只执行固定 dt 的整数子步，余数累积到下一帧，运动平滑且精度不变。
        单帧子步数不超过 MAX_SUBSTEPS_PER_FRAME，超出部分直接丢弃
        （宁可慢不卡帧），避免 accumulator 无限积压导致从高倍速切回慢速失效。

        Args:
            wall_seconds: 自上一帧以来的墙钟时间（秒）

        Returns:
            本帧实际执行的子步数
        """
        if wall_seconds <= 0.0:
            self.last_advance_capped = False
            return 0

        self._accumulator += self.simulation_rate * wall_seconds
        steps = int(self._accumulator / self.dt)
        if steps > MAX_SUBSTEPS_PER_FRAME:
            # 超出单帧上限的部分直接丢弃；若保留在 accumulator 中，
            # 高倍速运行产生的积压会让降速后仍长时间按上限速度推进。
            steps = MAX_SUBSTEPS_PER_FRAME
            self._accumulator = 0.0
            self.last_advance_capped = True
        else:
            self._accumulator -= steps * self.dt
            self.last_advance_capped = False

        for _ in range(steps):
            self._single_step()
        return steps
    
    def set_timing(self, timing) -> None:
        """
        安装或移除可选计时钩子（仅计时，不改变任何数值行为与时间步长）。

        timing 需提供（duck typing）：
            record(stage: str, seconds: float)     # 阶段：force/integrator/collision/trail/body_update/step
            record_count(stage: str, count: int)   # 计数：merges
        传 None 时关闭计时，_single_step 走无计时快速路径。
        """
        self._timing = timing
        self.gravity_solver.set_timing(timing)

    def _single_step(self) -> None:
        """
        执行单个物理时间步

        顺序：积分 -> 碰撞处理 -> 轨迹记录 -> 时间推进
        计时开启时主动上报各阶段耗时（不改变数值结果与时间步长）。
        """
        if len(self.bodies) == 0:
            return
        timing = self._timing
        if timing is None:
            # 无计时快速路径：与原始实现完全一致
            self._run_physics_step()
            return
        t0 = time.perf_counter()
        int_secs, col_secs, trail_secs = self._run_physics_step_timed(timing)
        total = time.perf_counter() - t0
        timing.record(
            'body_update', max(0.0, total - int_secs - col_secs - trail_secs)
        )
        timing.record('step', total)

    def _run_physics_step(self) -> None:
        """执行物理步（无计时路径，顺序：积分 -> 碰撞 -> 轨迹 -> 时间推进）。"""
        # 1. 数值积分（更新位置和速度）
        if isinstance(self.integrator, VelocityVerletIntegrator):
            self._cached_accelerations = self.integrator.step(
                self.bodies, self.dt, self._cached_accelerations
            )
        else:
            self.integrator.step(self.bodies, self.dt)

        # 2. 碰撞检测与融合
        self.bodies = self.collision_handler.resolve_collisions(self.bodies)
        # 碰撞后加速度缓存失效
        self._cached_accelerations = None

        # 3. 记录轨迹
        self._record_trajectories()

        # 4. 推进模拟时间
        self.simulation_time += self.dt

    def _run_physics_step_timed(self, timing):
        """
        带计时的物理步；与 _run_physics_step 数值等价。

        Returns:
            (integrator_secs, collision_secs, trail_secs)
        """
        t1 = time.perf_counter()
        # 1. 数值积分（force 阶段由 GravitySolver 上报）
        if isinstance(self.integrator, VelocityVerletIntegrator):
            self._cached_accelerations = self.integrator.step(
                self.bodies, self.dt, self._cached_accelerations
            )
        else:
            self.integrator.step(self.bodies, self.dt)
        int_secs = time.perf_counter() - t1
        timing.record('integrator', int_secs)

        # 2. 碰撞检测与融合
        t1 = time.perf_counter()
        before = len(self.bodies)
        self.bodies = self.collision_handler.resolve_collisions(self.bodies)
        col_secs = time.perf_counter() - t1
        timing.record('collision', col_secs)
        if len(self.bodies) < before:
            timing.record_count('merges', before - len(self.bodies))
        # 碰撞后加速度缓存失效
        self._cached_accelerations = None

        # 3. 记录轨迹
        t1 = time.perf_counter()
        self._record_trajectories()
        trail_secs = time.perf_counter() - t1
        timing.record('trail', trail_secs)

        # 4. 推进模拟时间
        self.simulation_time += self.dt
        return int_secs, col_secs, trail_secs
    
    def _record_trajectories(self) -> None:
        """
        记录当前帧的轨迹数据
        
        - 每个天体的个体轨迹（trail）
        - 全局轨迹历史（trajectory_history）
        """
        for body in self.bodies:
            # 记录个体轨迹
            body.trail.append(body.position.copy())
            
            # 记录到全局轨迹
            self.trajectory_history.append(body.position.copy())
    
    def center_of_mass(self) -> np.ndarray:
        """
        计算系统质心位置
        
        R_cm = sum(m_i * r_i) / sum(m_i)
        
        Returns:
            质心坐标 (x, y)
        """
        if not self.bodies:
            return np.zeros(2, dtype=np.float64)
        
        total_mass = sum(b.mass for b in self.bodies)
        weighted_pos = sum(b.mass * b.position for b in self.bodies)
        
        return weighted_pos / total_mass
    
    def total_momentum(self) -> np.ndarray:
        """
        计算系统总动量
        
        P = sum(m_i * v_i)
        
        Returns:
            总动量向量 (px, py)
        """
        if not self.bodies:
            return np.zeros(2, dtype=np.float64)
        
        return sum(b.momentum() for b in self.bodies)
    
    def kinetic_energy(self) -> float:
        """
        计算系统总动能
        
        KE = sum(0.5 * m_i * v_i^2)
        
        Returns:
            总动能
        """
        return sum(b.kinetic_energy() for b in self.bodies)
    
    def potential_energy(self) -> float:
        """
        计算系统总势能
        
        PE = -G * sum(m_i * m_j / r_ij)  (i < j)
        
        Returns:
            总势能（负值）
        """
        return self.gravity_solver.potential_energy(self.bodies)
    
    def total_energy(self) -> float:
        """
        计算系统总能量
        
        E = KE + PE
        
        Returns:
            总能量
        """
        return self.kinetic_energy() + self.potential_energy()
    
    def total_mass(self) -> float:
        """
        计算系统总质量
        
        Returns:
            总质量
        """
        return sum(b.mass for b in self.bodies)
    
    def body_count(self) -> int:
        """
        获取当前天体数量
        
        Returns:
            天体数量
        """
        return len(self.bodies)
    # ============================================================
    # 只读查询接口（供 UI / Formatter 使用，不修改物理状态）
    # ============================================================

    def get_body_state(self, index: int) -> dict:
        """
        获取指定天体的状态快照（只读）

        Args:
            index: 天体索引

        Returns:
            包含 name, mass, position, velocity, physical_radius, render_radius 的字典
            所有数值均为模拟单位
        """
        body = self.bodies[index]
        return {
            'name': body.name,
            'mass': body.mass,
            'position': body.position.copy(),
            'velocity': body.velocity.copy(),
            'physical_radius': body.physical_radius,
            'render_radius': body.render_radius,
            'color': body.color.copy(),
        }

    def body_acceleration(self, index: int) -> np.ndarray:
        """
        计算指定天体当前受到的引力加速度（只读）

        不修改物理状态，仅计算当前时刻的加速度。

        Args:
            index: 天体索引

        Returns:
            加速度向量 (ax, ay)（模拟单位）
        """
        if len(self.bodies) <= 1:
            return np.zeros(2, dtype=np.float64)
        return self.gravity_solver.compute_acceleration_single(self.bodies, index)

    def body_net_force(self, index: int) -> np.ndarray:
        """
        计算指定天体当前受到的净引力（只读）

        F = m * a

        Args:
            index: 天体索引

        Returns:
            力向量 (Fx, Fy)（模拟单位）
        """
        body = self.bodies[index]
        return body.mass * self.body_acceleration(index)

    def body_distances(self, index: int) -> np.ndarray:
        """
        计算指定天体到所有其他天体的距离（只读）

        Args:
            index: 天体索引

        Returns:
            距离数组，长度为 N-1（排除自身）
        """
        body = self.bodies[index]
        distances = []
        for j, other in enumerate(self.bodies):
            if j != index:
                distances.append(body.distance_to(other))
        return np.array(distances, dtype=np.float64)

    def body_kinetic_energy(self, index: int) -> float:
        """
        计算指定天体的动能（只读）

        Args:
            index: 天体索引

        Returns:
            动能（模拟单位）
        """
        return self.bodies[index].kinetic_energy()

    def get_all_body_states(self) -> list:
        """
        获取所有天体的状态快照列表（只读）

        Returns:
            状态字典列表
        """
        return [self.get_body_state(i) for i in range(len(self.bodies))]

    def snapshot(self) -> dict:
        """
        获取当前模拟状态的完整快照（只读）

        用于模式切换前后验证物理状态一致性。

        Returns:
            包含所有物理状态的字典
        """
        return {
            'simulation_time': self.simulation_time,
            'dt': self.dt,
            'time_scale': self.time_scale,
            'body_count': len(self.bodies),
            'bodies': [
                {
                    'name': b.name,
                    'mass': b.mass,
                    'position': b.position.copy(),
                    'velocity': b.velocity.copy(),
                    'physical_radius': b.physical_radius,
                    'render_radius': b.render_radius,
                }
                for b in self.bodies
            ],
        }






