"""
质心参考系管理模块

计算系统质心、总动量，提供动量修正功能
不修改物理引擎，只读取和计算
"""

import numpy as np
from typing import Tuple, List, Optional
from .body import Body


class ReferenceFrame:
    """
    质心参考系管理器
    
    计算系统质心位置和速度，提供动量修正功能
    """
    
    def __init__(self):
        """初始化参考系管理器"""
        self._center_of_mass = np.array([0.0, 0.0], dtype=np.float64)
        self._center_of_mass_velocity = np.array([0.0, 0.0], dtype=np.float64)
        self._total_mass = 0.0
        self._total_momentum = np.array([0.0, 0.0], dtype=np.float64)
    
    def compute_center_of_mass(self, bodies: List[Body]) -> np.ndarray:
        """
        计算系统质心位置
        
        R_cm = Σ(m_i * r_i) / Σm_i
        
        Args:
            bodies: 天体列表
            
        Returns:
            质心位置 (x, y)
        """
        if not bodies:
            return np.array([0.0, 0.0], dtype=np.float64)
        
        total_mass = sum(b.mass for b in bodies)
        if total_mass < 1e-10:
            return np.array([0.0, 0.0], dtype=np.float64)
        
        weighted_position = sum(b.mass * b.position for b in bodies)
        self._center_of_mass = weighted_position / total_mass
        self._total_mass = total_mass
        
        return self._center_of_mass.copy()
    
    def compute_center_of_mass_velocity(self, bodies: List[Body]) -> np.ndarray:
        """
        计算系统质心速度
        
        V_cm = Σ(m_i * v_i) / Σm_i
        
        Args:
            bodies: 天体列表
            
        Returns:
            质心速度 (vx, vy)
        """
        if not bodies:
            return np.array([0.0, 0.0], dtype=np.float64)
        
        total_mass = sum(b.mass for b in bodies)
        if total_mass < 1e-10:
            return np.array([0.0, 0.0], dtype=np.float64)
        
        total_momentum = sum(b.mass * b.velocity for b in bodies)
        self._center_of_mass_velocity = total_momentum / total_mass
        self._total_momentum = total_momentum
        
        return self._center_of_mass_velocity.copy()
    
    def compute_total_momentum(self, bodies: List[Body]) -> np.ndarray:
        """
        计算系统总动量
        
        P = Σ(m_i * v_i)
        
        Args:
            bodies: 天体列表
            
        Returns:
            总动量 (px, py)
        """
        if not bodies:
            return np.array([0.0, 0.0], dtype=np.float64)
        
        self._total_momentum = sum(b.mass * b.velocity for b in bodies)
        return self._total_momentum.copy()
    
    def compute_all(self, bodies: List[Body]) -> dict:
        """
        计算所有参考系信息
        
        Args:
            bodies: 天体列表
            
        Returns:
            包含质心位置、速度、总质量、总动量的字典
        """
        com_pos = self.compute_center_of_mass(bodies)
        com_vel = self.compute_center_of_mass_velocity(bodies)
        total_momentum = self.compute_total_momentum(bodies)
        
        return {
            'center_of_mass': com_pos,
            'center_of_mass_velocity': com_vel,
            'total_mass': self._total_mass,
            'total_momentum': total_momentum,
        }
    
    def get_velocity_offset_for_zero_momentum(self, bodies: List[Body]) -> np.ndarray:
        """
        计算使总动量为零所需的速度偏移
        
        V_offset = V_cm = P / Σm
        
        Args:
            bodies: 天体列表
            
        Returns:
            速度偏移 (vx, vy)
        """
        return self.compute_center_of_mass_velocity(bodies)
    
    def apply_momentum_correction(self, bodies: List[Body]) -> None:
        """
        应用动量修正，使总动量为零
        
        对每个天体：v_i_new = v_i - V_cm
        
        注意：这会修改天体的速度！
        
        Args:
            bodies: 天体列表
        """
        if not bodies:
            return
        
        v_cm = self.compute_center_of_mass_velocity(bodies)
        
        for body in bodies:
            body.velocity = body.velocity - v_cm
    
    def get_relative_position(self, body: Body) -> np.ndarray:
        """
        获取天体相对于质心的位置
        
        Args:
            body: 天体
            
        Returns:
            相对位置 (x, y)
        """
        return body.position - self._center_of_mass
    
    def get_relative_velocity(self, body: Body) -> np.ndarray:
        """
        获取天体相对于质心的速度
        
        Args:
            body: 天体
            
        Returns:
            相对速度 (vx, vy)
        """
        return body.velocity - self._center_of_mass_velocity
    
    @property
    def center_of_mass(self) -> np.ndarray:
        """获取质心位置"""
        return self._center_of_mass.copy()
    
    @property
    def center_of_mass_velocity(self) -> np.ndarray:
        """获取质心速度"""
        return self._center_of_mass_velocity.copy()
    
    @property
    def total_mass(self) -> float:
        """获取总质量"""
        return self._total_mass
    
    @property
    def total_momentum(self) -> np.ndarray:
        """获取总动量"""
        return self._total_momentum.copy()
