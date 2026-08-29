"""
高性能引力计算模块
在原有基础上增加GPU加速支持
"""
import numpy as np
import time
import warnings
from typing import List, Optional
from .body import Body
from .constants import G, SOFTENING

# 尝试导入CuPy（GPU加速）
CUPY_AVAILABLE = False
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    print("[GravityOpt] CuPy available - GPU acceleration enabled")
except Exception:
    pass  # 静默失败

class GravitySolverOpt:
    """
    引力求解器（支持GPU加速）
    """
    def __init__(self, softening: float = SOFTENING, use_gpu: bool = True):
        self.softening = softening
        self._timing = None
        self.use_gpu = use_gpu and CUPY_AVAILABLE
        
    def set_timing(self, timing):
        self._timing = timing

    def compute_accelerations(self, bodies: List[Body]) -> np.ndarray:
        """计算所有天体的加速度（GPU/CPU自动选择）"""
        if self._timing is None:
            return self._compute_accelerations_impl(bodies)
        
        t0 = time.perf_counter()
        try:
            return self._compute_accelerations_impl(bodies)
        finally:
            self._timing.record('force', time.perf_counter() - t0)
    
    def _compute_accelerations_impl(self, bodies: List[Body]) -> np.ndarray:
        """加速度计算的实现"""
        n = len(bodies)
        if n == 0:
            return np.zeros((0, 2), dtype=np.float64)
        
        # 根据配置选择GPU或CPU
        if self.use_gpu:
            return self._compute_gpu(bodies)
        else:
            return self._compute_cpu(bodies)
    
    def _compute_gpu(self, bodies: List[Body]) -> np.ndarray:
        """GPU加速实现"""
        n = len(bodies)
        
        # 提取位置和质量
        positions = np.array([b.position for b in bodies], dtype=np.float64)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)
        
        # 转换到GPU
        positions_cp = cp.asarray(positions)
        masses_cp = cp.asarray(masses)
        soft_cp = cp.float64(self.softening)
        
        # GPU计算（与原版逻辑相同）
        diff = positions_cp[cp.newaxis, :, :] - positions_cp[:, cp.newaxis, :]
        dist_sq = cp.sum(diff ** 2, axis=2) + soft_cp ** 2
        cp.fill_diagonal(dist_sq, 1.0)
        inv_dist_cube = 1.0 / cp.power(dist_sq, 1.5)
        cp.fill_diagonal(inv_dist_cube, 0.0)
        weights = masses_cp[cp.newaxis, :] * inv_dist_cube
        accelerations_cp = G * cp.sum(weights[:, :, cp.newaxis] * diff, axis=1)
        
        # 转回CPU
        return cp.asnumpy(accelerations_cp)
    
    def _compute_cpu(self, bodies: List[Body]) -> np.ndarray:
        """CPU实现（与原版完全相同）"""
        n = len(bodies)
        if n == 0:
            return np.zeros((0, 2), dtype=np.float64)
        
        # 提取位置和质量
        positions = np.array([b.position for b in bodies], dtype=np.float64)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)
        
        # 计算所有 pairwise 位移差
        diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]
        dist_sq = np.sum(diff ** 2, axis=2) + self.softening ** 2
        np.fill_diagonal(dist_sq, 1.0)
        inv_dist_cube = 1.0 / (dist_sq ** 1.5)
        np.fill_diagonal(inv_dist_cube, 0.0)
        weights = masses[np.newaxis, :] * inv_dist_cube
        accelerations = G * np.sum(weights[:, :, np.newaxis] * diff, axis=1)
        
        return accelerations

    def compute_acceleration_single(self, bodies: List[Body], index: int) -> np.ndarray:
        """计算单个天体的加速度"""
        if len(bodies) <= 1:
            return np.zeros(2, dtype=np.float64)

        target = bodies[index]
        acc = np.zeros(2, dtype=np.float64)
        for j, other in enumerate(bodies):
            if j == index:
                continue
            dx = other.position[0] - target.position[0]
            dy = other.position[1] - target.position[1]
            dist_sq = dx * dx + dy * dy + self.softening ** 2
            factor = G * other.mass / (dist_sq ** 1.5)
            acc[0] += factor * dx
            acc[1] += factor * dy
        return acc

    def potential_energy(self, bodies: List[Body]) -> float:
        """计算系统势能"""
        n = len(bodies)
        if n < 2:
            return 0.0
        
        positions = np.array([b.position for b in bodies], dtype=np.float64)
        masses = np.array([b.mass for b in bodies], dtype=np.float64)
        
        diff = positions[np.newaxis, :, :] - positions[:, np.newaxis, :]
        dist = np.sqrt(np.sum(diff ** 2, axis=2) + self.softening ** 2)
        mass_product = masses[:, np.newaxis] * masses[np.newaxis, :]
        upper_tri = np.triu_indices(n, k=1)
        energy = -G * np.sum(mass_product[upper_tri] / dist[upper_tri])
        
        return float(energy)
