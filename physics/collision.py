"""
碰撞检测与处理模块

实现天体碰撞检测与融合
遵循质量守恒和动量守恒
所有物理量使用模拟单位（Simulation Units）
"""

from collections import deque

import numpy as np
from typing import List, Tuple
from .body import Body
from .constants import (
    COLLISION_FACTOR, RADIUS_MERGE_EXPONENT, MAX_TRAJECTORY_LENGTH,
)


class CollisionHandler:
    """
    碰撞处理器
    
    检测天体之间的碰撞并执行融合
    碰撞检测仅使用 physical_radius，render_radius 不参与物理计算
    """
    
    def __init__(self, collision_factor: float = COLLISION_FACTOR):
        """
        初始化碰撞处理器
        
        Args:
            collision_factor: 碰撞距离阈值系数
        """
        self.collision_factor = collision_factor
    
    def detect_collisions(self, bodies: List[Body]) -> List[Tuple[int, int]]:
        """
        检测所有碰撞对
        
        碰撞条件：两体距离 < (physical_radius_1 + physical_radius_2) * collision_factor
        仅使用 physical_radius，render_radius 不影响碰撞检测
        
        Args:
            bodies: 天体列表
            
        Returns:
            碰撞对列表 [(i, j), ...]
        """
        collisions = []
        n = len(bodies)
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = bodies[i].distance_to(bodies[j])
                threshold = (bodies[i].physical_radius + bodies[j].physical_radius) * self.collision_factor
                
                if dist < threshold:
                    collisions.append((i, j))
        
        return collisions
    
    def merge_bodies(self, body_a: Body, body_b: Body) -> Body:
        """
        融合两个天体
        
        守恒量：
        - 质量守恒：m_new = m_a + m_b
        - 动量守恒：m_new * v_new = m_a * v_a + m_b * v_b
        - physical_radius：基于体积守恒 r_new = (r_a^3 + r_b^3)^(1/3)
        - render_radius：基于体积守恒，独立于 physical_radius
        - 位置：质量加权平均（质心）
        
        Args:
            body_a: 第一个天体
            body_b: 第二个天体
            
        Returns:
            融合后的新天体
        """
        # 质量守恒
        new_mass = body_a.mass + body_b.mass
        
        # 动量守恒 -> 速度
        total_momentum = body_a.momentum() + body_b.momentum()
        new_velocity = total_momentum / new_mass
        
        # 体积守恒 -> physical_radius（仅物理半径参与碰撞物理）
        new_physical_radius = (
            body_a.physical_radius ** 3 + body_b.physical_radius ** 3
        ) ** RADIUS_MERGE_EXPONENT
        
        # 体积守恒 -> render_radius（独立计算，不受 physical_radius 污染）
        new_render_radius = (
            body_a.render_radius ** 3 + body_b.render_radius ** 3
        ) ** RADIUS_MERGE_EXPONENT
        
        # 位置：质量加权平均（质心位置）
        new_position = (
            body_a.mass * body_a.position + body_b.mass * body_b.position
        ) / new_mass
        
        # 颜色：质量加权平均
        new_color = (
            body_a.mass * body_a.color + body_b.mass * body_b.color
        ) / new_mass
        
        # 名称：合并名称
        if body_a.name and body_b.name:
            new_name = f"{body_a.name}+{body_b.name}"
        else:
            new_name = body_a.name or body_b.name
        
        # 创建融合后的天体（physical_radius 和 render_radius 分别设置）
        merged = Body(
            name=new_name,
            mass=new_mass,
            physical_radius=new_physical_radius,
            position=tuple(new_position),
            velocity=tuple(new_velocity),
            color=tuple(new_color),
            render_radius=new_render_radius
        )
        
        # 合并轨迹历史（deque 自动截断到上限）
        merged.trail = deque(
            list(body_a.trail) + list(body_b.trail),
            maxlen=MAX_TRAJECTORY_LENGTH,
        )
        
        return merged
    
    def resolve_collisions(self, bodies: List[Body]) -> List[Body]:
        """
        处理所有碰撞，返回融合后的天体列表
        
        使用贪心策略：按碰撞对顺序依次融合
        注意：一次调用可能无法处理所有碰撞（级联碰撞需要多次调用）
        
        Args:
            bodies: 天体列表
            
        Returns:
            碰撞处理后的天体列表
        """
        collisions = self.detect_collisions(bodies)
        
        if not collisions:
            return bodies
        
        # 标记已被融合的天体
        merged_indices = set()
        new_bodies = []
        
        for i, j in collisions:
            # 如果两个天体都还没被融合
            if i not in merged_indices and j not in merged_indices:
                # 融合它们
                merged = self.merge_bodies(bodies[i], bodies[j])
                new_bodies.append(merged)
                merged_indices.add(i)
                merged_indices.add(j)
        
        # 添加未参与碰撞的天体
        for k, body in enumerate(bodies):
            if k not in merged_indices:
                new_bodies.append(body)
        
        return new_bodies
