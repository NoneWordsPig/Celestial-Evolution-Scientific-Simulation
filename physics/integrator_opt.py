import numpy as np
from typing import List, Optional
from .gravity_opt import GravitySolverOpt
from .body import Body

class RK4IntegratorOpt:
    """RK4积分器（与原版逻辑相同，使用优化引力求解器）"""
    def __init__(self, gravity_solver: GravitySolverOpt):
        self.gravity_solver = gravity_solver

    def step(self, bodies: List[Body], dt: float) -> None:
        """执行一步RK4积分"""
        n = len(bodies)
        if n == 0:
            return

        # 保存初始状态
        initial_positions = np.array([b.position for b in bodies], dtype=np.float64)
        initial_velocities = np.array([b.velocity for b in bodies], dtype=np.float64)

        # k1
        k1_accelerations = self.gravity_solver.compute_accelerations(bodies)
        k1_velocities = initial_velocities.copy()

        # k2
        half_dt = 0.5 * dt
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + half_dt * k1_velocities[i]
            body.velocity = initial_velocities[i] + half_dt * k1_accelerations[i]
        
        k2_accelerations = self.gravity_solver.compute_accelerations(bodies)
        k2_velocities = np.array([b.velocity for b in bodies], dtype=np.float64)

        # k3
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + half_dt * k2_velocities[i]
            body.velocity = initial_velocities[i] + half_dt * k2_accelerations[i]
        
        k3_accelerations = self.gravity_solver.compute_accelerations(bodies)
        k3_velocities = np.array([b.velocity for b in bodies], dtype=np.float64)

        # k4
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + dt * k3_velocities[i]
            body.velocity = initial_velocities[i] + dt * k3_accelerations[i]
        
        k4_accelerations = self.gravity_solver.compute_accelerations(bodies)
        k4_velocities = np.array([b.velocity for b in bodies], dtype=np.float64)

        # 最终更新
        inv_6_dt = dt / 6.0
        two_inv_6_dt = 2.0 * inv_6_dt
        
        for i, body in enumerate(bodies):
            # 位置更新
            body.position = initial_positions[i] + inv_6_dt * (
                k1_velocities[i] + 2.0 * k2_velocities[i] + 2.0 * k3_velocities[i] + k4_velocities[i]
            )
            # 速度更新
            body.velocity = initial_velocities[i] + inv_6_dt * (
                k1_accelerations[i] + 2.0 * k2_accelerations[i] + 2.0 * k3_accelerations[i] + k4_accelerations[i]
            )
