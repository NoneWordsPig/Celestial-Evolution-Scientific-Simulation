"""
引力计算模块

实现 Newton 万有引力的 O(N^2) 计算
使用 NumPy 向量化加速
"""

import numpy as np
import time
from typing import List
from .body import Body
from .constants import G, SOFTENING


class GravitySolver:
    """
    引力求解器
    
    计算多体系统中所有天体之间的万有引力
    使用软化因子避免距离为零时的奇点
    """
    
    def __init__(self, softening: float = SOFTENING):
        """
        初始化引力求解器
        
        Args:
            softening: 软化因子，防止奇点
        """
        self.softening = softening
        # 可选计时钩子（None = 关闭，无额外开销）；不参与任何数值计算
        self._timing = None
    
    def set_timing(self, timing) -> None:
        """
        安装或移除可选计时钩子（仅计时，不改变任何数值计算）。
        
        计时开启时 compute_accelerations 会上报 'force' 阶段耗时（秒）。
        传 None 关闭，恢复无计时路径。
        """
        self._timing = timing
    
    def compute_accelerations(self, bodies: List[Body]) -> np.ndarray:
        """
        计算所有天体的加速度（O(N^2) 向量化版本）
        
        对每一对天体计算引力：
            F = G * m_i * m_j / (r^2 + softening^2)
            a_i = F / m_i
        
        Args:
            bodies: 天体列表
            
        Returns:
            accelerations: shape (N, 2) 的数组，每个天体的加速度
        """
        timing = self._timing
        if timing is None:
            return self._compute_accelerations_impl(bodies)
        t0 = time.perf_counter()
        try:
            return self._compute_accelerations_impl(bodies)
        finally:
            timing.record('force', time.perf_counter() - t0)
    
    def _compute_accelerations_impl(self, bodies: List[Body]) -> np.ndarray:
        """加速度计算的数值实现；与计时无关，不改变任何数值。"""
        n = len(bodies)
        if n == 0:
            return np.zeros((0, 2), dtype=np.float64)
        
        # 提取位置和质量为 NumPy 数组
        positions = np.array([b.position for b in bodies], dtype=np.float64)  # (N, 2)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)  # (N,)
        
        # 计算所有 pairwise 位移差
        # diff[i, j] = positions[j] - positions[i]
        diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]  # (N, N, 2)
        
        # 计算距离的平方（加软化因子）
        dist_sq = np.sum(diff ** 2, axis=2) + self.softening ** 2  # (N, N)
        
        # 将对角线设为安全值（排除自身引力，避免 softening=0 时除零）
        np.fill_diagonal(dist_sq, 1.0)
        
        # 计算引力大小：F / (m_i * m_j) = G / dist_sq
        # 然后乘以方向向量 diff / dist
        # 综合：acceleration on i from j = G * m_j * diff[i,j] / dist_sq^(3/2)
        inv_dist_cube = 1.0 / (dist_sq ** 1.5)  # (N, N)
        
        # 将对角线设为零（排除自身引力）
        np.fill_diagonal(inv_dist_cube, 0.0)
        
        # 计算加速度：a_i = G * sum_j(m_j * diff[i,j] * inv_dist_cube[i,j])
        # weights[j] = m_j * inv_dist_cube[i, j]
        weights = masses[np.newaxis, :] * inv_dist_cube  # (N, N)
        accelerations = G * np.sum(weights[:, :, np.newaxis] * diff, axis=1)  # (N, 2)
        
        return accelerations
    
    def compute_acceleration_single(self, bodies: List[Body], index: int) -> np.ndarray:
        """
        计算单个天体受到的加速度（用于 RK4 中间步骤）
        
        Args:
            bodies: 天体列表
            index: 目标天体索引
            
        Returns:
            加速度向量 (ax, ay)
        """
        if len(bodies) <= 1:
            return np.zeros(2, dtype=np.float64)
        
        target = bodies[index]
        acc = np.zeros(2, dtype=np.float64)
        
        for j, other in enumerate(bodies):
            if j == index:
                continue
            
            # 位移向量
            dx = other.position[0] - target.position[0]
            dy = other.position[1] - target.position[1]
            
            # 距离平方（加软化）
            dist_sq = dx * dx + dy * dy + self.softening ** 2
            
            # 引力加速度大小
            factor = G * other.mass / (dist_sq ** 1.5)
            
            acc[0] += factor * dx
            acc[1] += factor * dy
        
        return acc
    
    def potential_energy(self, bodies: List[Body]) -> float:
        """
        计算系统的引力势能
        
        U = -G * sum(m_i * m_j / r_ij)  (i < j)
        
        Args:
            bodies: 天体列表
            
        Returns:
            总势能（负值）
        """
        n = len(bodies)
        if n < 2:
            return 0.0
        
        positions = np.array([b.position for b in bodies], dtype=np.float64)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)
        
        # 计算所有 pairwise 距离
        diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]
        dist = np.sqrt(np.sum(diff ** 2, axis=2) + self.softening ** 2)
        
        # 计算质量乘积矩阵
        mass_product = masses[:, np.newaxis] * masses[np.newaxis, :]
        
        # 只取上三角（避免重复计算）
        upper_tri = np.triu_indices(n, k=1)
        
        # 势能 = -G * sum(m_i * m_j / r_ij)
        energy = -G * np.sum(mass_product[upper_tri] / dist[upper_tri])
        
        return float(energy)
