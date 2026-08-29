"""
天体数据类模块

定义 Body 类，表示模拟中的单个天体
使用模拟单位（Simulation Units）：G=1, MU=1, DU=1, TU=1
"""

from collections import deque

import numpy as np
from typing import Tuple, Optional

from .constants import MAX_TRAJECTORY_LENGTH


class Body:
    """
    天体类
    
    所有物理量均使用模拟单位（Simulation Units）：
    - mass: 质量单位 MU
    - position: 距离单位 DU
    - velocity: 速度单位 DU/TU
    - physical_radius: 物理半径 DU（用于碰撞检测和引力计算）
    - render_radius: 渲染半径 DU（用于 OpenGL 绘制，可独立设置）
    
    属性:
        name: 天体名称
        mass: 质量 (MU)
        physical_radius: 物理半径 (DU)，用于碰撞和物理计算
        render_radius: 渲染半径 (DU)，用于视觉显示
        position: 位置 (x, y) (DU)
        velocity: 速度 (vx, vy) (DU/TU)
        color: 颜色 (R, G, B) 归一化到 0-1
    """
    
    def __init__(
        self,
        name: str = "",
        mass: float = 1.0,
        physical_radius: float = 1.0,
        position: Tuple[float, float] = (0.0, 0.0),
        velocity: Tuple[float, float] = (0.0, 0.0),
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        render_radius: Optional[float] = None
    ):
        """
        初始化天体
        
        Args:
            name: 天体名称
            mass: 质量 (MU)，必须 > 0
            physical_radius: 物理半径 (DU)，必须 > 0，用于碰撞检测和物理计算
            position: 初始位置 (x, y) (DU)
            velocity: 初始速度 (vx, vy) (DU/TU)
            color: RGB 颜色，归一化到 0-1
            render_radius: 渲染半径 (DU)，用于 OpenGL 绘制。
                          若为 None，则默认等于 physical_radius。
                          可独立设置以增强视觉效果，不影响物理计算。
        """
        self.name = name
        self.mass = max(mass, 1e-10)  # 防止零质量
        self.physical_radius = max(physical_radius, 1e-10)  # 物理半径，防止零值
        
        # 渲染半径：默认等于物理半径，可独立设置
        # 不强制最小可见尺寸，保留真实半径映射值；仅防止零/负值
        if render_radius is not None:
            self.render_radius = max(render_radius, 1e-10)
        else:
            self.render_radius = self.physical_radius
        
        self.position = np.array(position, dtype=np.float64)
        self.velocity = np.array(velocity, dtype=np.float64)
        self.color = np.array(color, dtype=np.float32)
        
        # 轨迹历史（用于渲染）
        # 轨迹历史：deque 自动截断到上限，O(1) 追加/淘汰
        self.trail = deque(maxlen=MAX_TRAJECTORY_LENGTH)
    
    @property
    def radius(self) -> float:
        """
        向后兼容属性：返回 physical_radius
        
        新代码应直接使用 physical_radius 或 render_radius
        """
        return self.physical_radius
    
    def kinetic_energy(self) -> float:
        """
        计算天体的动能
        
        Returns:
            动能 = 0.5 * m * v^2 (MU * (DU/TU)^2)
        """
        v_squared = np.sum(self.velocity ** 2)
        return 0.5 * self.mass * v_squared
    
    def momentum(self) -> np.ndarray:
        """
        计算天体的动量
        
        Returns:
            动量向量 (px, py) = m * (vx, vy) (MU * DU/TU)
        """
        return self.mass * self.velocity
    
    def distance_to(self, other: 'Body') -> float:
        """
        计算到另一个天体的距离
        
        Args:
            other: 另一个天体
            
        Returns:
            欧几里得距离 (DU)
        """
        return np.linalg.norm(self.position - other.position)
    
    def circular_orbital_velocity(self, central_mass: float, distance: float) -> float:
        """
        计算在给定中心质量下的圆轨道速度
        
        v = sqrt(G * M / r)，在模拟单位中 G=1
        
        Args:
            central_mass: 中心天体质量 (MU)
            distance: 轨道半径 (DU)
            
        Returns:
            圆轨道速度 (DU/TU)
        """
        return np.sqrt(central_mass / distance)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (f"Body(name='{self.name}', mass={self.mass:.2f}, "
                f"phys_r={self.physical_radius:.2f}, "
                f"render_r={self.render_radius:.2f}, pos={self.position})")
