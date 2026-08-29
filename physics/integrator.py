"""
数值积分器模块

实现 Velocity Verlet（默认）和 RK4 积分器
用于求解天体运动方程
"""

import numpy as np
from typing import List, Callable
from .body import Body
from .gravity import GravitySolver


class VelocityVerletIntegrator:
    """
    Velocity Verlet 积分器（默认）
    
    辛积分器，具有良好的能量守恒特性
    算法：
        1. x(t+dt) = x(t) + v(t)*dt + 0.5*a(t)*dt^2
        2. 计算 a(t+dt)
        3. v(t+dt) = v(t) + 0.5*(a(t) + a(t+dt))*dt
    """
    
    def __init__(self, gravity_solver: GravitySolver):
        """
        初始化积分器
        
        Args:
            gravity_solver: 引力求解器实例
        """
        self.gravity_solver = gravity_solver
    
    def step(self, bodies: List[Body], dt: float, accelerations: np.ndarray = None) -> np.ndarray:
        """
        执行一步 Velocity Verlet 积分
        
        Args:
            bodies: 天体列表
            dt: 时间步长
            accelerations: 当前加速度（可选，如为 None 则重新计算）
            
        Returns:
            新的加速度数组（用于下一步）
        """
        n = len(bodies)
        if n == 0:
            return np.zeros((0, 2), dtype=np.float64)
        
        # 步骤 1: 计算当前加速度（如果未提供）
        if accelerations is None:
            accelerations = self.gravity_solver.compute_accelerations(bodies)
        
        # 步骤 2: 更新位置
        # x(t+dt) = x(t) + v(t)*dt + 0.5*a(t)*dt^2
        for i, body in enumerate(bodies):
            body.position = body.position + body.velocity * dt + 0.5 * accelerations[i] * dt ** 2
        
        # 步骤 3: 计算新的加速度 a(t+dt)
        new_accelerations = self.gravity_solver.compute_accelerations(bodies)
        
        # 步骤 4: 更新速度
        # v(t+dt) = v(t) + 0.5*(a(t) + a(t+dt))*dt
        for i, body in enumerate(bodies):
            body.velocity = body.velocity + 0.5 * (accelerations[i] + new_accelerations[i]) * dt
        
        return new_accelerations


class RK4Integrator:
    """
    Runge-Kutta 4 阶积分器
    
    高精度积分器，但计算开销较大（每步需 4 次引力计算）
    算法：
        k1 = f(t, y)
        k2 = f(t + dt/2, y + dt/2 * k1)
        k3 = f(t + dt/2, y + dt/2 * k2)
        k4 = f(t + dt, y + dt * k3)
        y(t+dt) = y(t) + dt/6 * (k1 + 2*k2 + 2*k3 + k4)
    """
    
    def __init__(self, gravity_solver: GravitySolver):
        """
        初始化 RK4 积分器
        
        Args:
            gravity_solver: 引力求解器实例
        """
        self.gravity_solver = gravity_solver
    
    def step(self, bodies: List[Body], dt: float) -> None:
        """
        执行一步 RK4 积分
        
        Args:
            bodies: 天体列表
            dt: 时间步长
        """
        n = len(bodies)
        if n == 0:
            return
        
        # 保存初始状态
        initial_positions = np.array([b.position.copy() for b in bodies])
        initial_velocities = np.array([b.velocity.copy() for b in bodies])
        
        # k1: 在 t 时刻的导数
        k1_acc = self.gravity_solver.compute_accelerations(bodies)
        k1_v = np.array([b.velocity.copy() for b in bodies])
        
        # k2: 在 t + dt/2 时刻的导数（使用 k1 预测）
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + 0.5 * dt * k1_v[i]
            body.velocity = initial_velocities[i] + 0.5 * dt * k1_acc[i]
        k2_acc = self.gravity_solver.compute_accelerations(bodies)
        k2_v = np.array([b.velocity.copy() for b in bodies])
        
        # k3: 在 t + dt/2 时刻的导数（使用 k2 预测）
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + 0.5 * dt * k2_v[i]
            body.velocity = initial_velocities[i] + 0.5 * dt * k2_acc[i]
        k3_acc = self.gravity_solver.compute_accelerations(bodies)
        k3_v = np.array([b.velocity.copy() for b in bodies])
        
        # k4: 在 t + dt 时刻的导数（使用 k3 预测）
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + dt * k3_v[i]
            body.velocity = initial_velocities[i] + dt * k3_acc[i]
        k4_acc = self.gravity_solver.compute_accelerations(bodies)
        k4_v = np.array([b.velocity.copy() for b in bodies])
        
        # 加权平均更新
        for i, body in enumerate(bodies):
            body.position = initial_positions[i] + (dt / 6.0) * (
                k1_v[i] + 2 * k2_v[i] + 2 * k3_v[i] + k4_v[i]
            )
            body.velocity = initial_velocities[i] + (dt / 6.0) * (
                k1_acc[i] + 2 * k2_acc[i] + 2 * k3_acc[i] + k4_acc[i]
            )


class IntegratorFactory:
    """
    积分器工厂
    
    根据配置创建不同类型的积分器
    """
    
    @staticmethod
    def create(integrator_type: str, gravity_solver: GravitySolver):
        """
        创建积分器实例
        
        Args:
            integrator_type: 积分器类型 ('verlet' 或 'rk4')
            gravity_solver: 引力求解器实例
            
        Returns:
            积分器实例
        """
        if integrator_type.lower() == 'verlet':
            return VelocityVerletIntegrator(gravity_solver)
        elif integrator_type.lower() == 'rk4':
            return RK4Integrator(gravity_solver)
        else:
            raise ValueError(f"Unknown integrator type: {integrator_type}")
