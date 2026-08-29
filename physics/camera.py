"""
Camera 模块

管理视图变换：World Coordinates → Screen Coordinates
不修改 Physics Engine 的世界坐标
"""

import numpy as np
from typing import Tuple


class Camera:
    """
    摄像机类
    
    负责：
    - 存储视图状态（center, zoom）
    - 坐标变换（world ↔ screen）
    - 缩放（以鼠标位置为中心）
    - 平移（拖拽）
    """
    
    def __init__(
        self,
        viewport_width: int = 800,
        viewport_height: int = 600,
        center_x: float = 0.0,
        center_y: float = 0.0,
        zoom: float = 1.0,
        min_zoom: float = 0.001,
        max_zoom: float = 2000.0
    ):
        """
        初始化摄像机
        
        Args:
            viewport_width: 视口宽度（像素）
            viewport_height: 视口高度（像素）
            center_x: 视图中心的世界 X 坐标（DU）
            center_y: 视图中心的世界 Y 坐标（DU）
            zoom: 缩放级别（像素/DU）
            min_zoom: 最小缩放
            max_zoom: 最大缩放
        """
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.center_x = center_x
        self.center_y = center_y
        self.zoom = zoom
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        
        # 默认缩放（用于 reset）
        self._default_zoom = zoom
        self._default_center = (center_x, center_y)
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        世界坐标 → 屏幕坐标
        
        变换公式：
        screen_x = (world_x - center_x) * zoom + viewport_width / 2
        screen_y = -(world_y - center_y) * zoom + viewport_height / 2  # Y 轴翻转
        
        Args:
            world_x: 世界 X 坐标（DU）
            world_y: 世界 Y 坐标（DU）
            
        Returns:
            (screen_x, screen_y) 屏幕坐标（像素）
        """
        screen_x = (world_x - self.center_x) * self.zoom + self.viewport_width / 2.0
        screen_y = -(world_y - self.center_y) * self.zoom + self.viewport_height / 2.0
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        屏幕坐标 → 世界坐标
        
        逆变换：
        world_x = (screen_x - viewport_width / 2) / zoom + center_x
        world_y = -(screen_y - viewport_height / 2) / zoom + center_y
        
        Args:
            screen_x: 屏幕 X 坐标（像素）
            screen_y: 屏幕 Y 坐标（像素）
            
        Returns:
            (world_x, world_y) 世界坐标（DU）
        """
        world_x = (screen_x - self.viewport_width / 2.0) / self.zoom + self.center_x
        world_y = -(screen_y - self.viewport_height / 2.0) / self.zoom + self.center_y
        return world_x, world_y
    
    def zoom_at_point(
        self,
        screen_x: float,
        screen_y: float,
        zoom_factor: float
    ) -> None:
        """
        以屏幕点为中心进行缩放
        
        保持该点在世界坐标中的位置不变
        
        Args:
            screen_x: 缩放中心的屏幕 X 坐标
            screen_y: 缩放中心的屏幕 Y 坐标
            zoom_factor: 缩放因子（>1 放大，<1 缩小）
        """
        # 记录缩放前该点的屏幕坐标对应的世界坐标
        world_x, world_y = self.screen_to_world(screen_x, screen_y)
        
        # 应用缩放
        new_zoom = self.zoom * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        self.zoom = new_zoom
        
        # 调整 center，使该世界点仍然映射到相同的屏幕点
        # screen_x = (world_x - new_center_x) * new_zoom + viewport_width / 2
        # => new_center_x = world_x - (screen_x - viewport_width / 2) / new_zoom
        self.center_x = world_x - (screen_x - self.viewport_width / 2.0) / self.zoom
        self.center_y = world_y + (screen_y - self.viewport_height / 2.0) / self.zoom
    
    def pan(self, dx_pixels: float, dy_pixels: float) -> None:
        """
        平移视图（拖拽）
        
        Args:
            dx_pixels: 屏幕 X 方向的像素偏移
            dy_pixels: 屏幕 Y 方向的像素偏移
        """
        # 屏幕偏移转换为世界偏移
        # 注意 Y 轴翻转
        self.center_x -= dx_pixels / self.zoom
        self.center_y += dy_pixels / self.zoom
    
    def reset(self) -> None:
        """重置摄像机到默认状态"""
        self.center_x, self.center_y = self._default_center
        self.zoom = self._default_zoom
    
    def set_default(self, center_x: float, center_y: float, zoom: float) -> None:
        """
        设置默认状态（用于 reset）
        
        Args:
            center_x: 默认中心 X
            center_y: 默认中心 Y
            zoom: 默认缩放
        """
        self._default_center = (center_x, center_y)
        self._default_zoom = zoom
    
    def fit_all_bodies(
        self,
        positions: np.ndarray,
        padding: float = 0.1
    ) -> None:
        """
        调整视图使所有天体进入视野
        
        Args:
            positions: 天体位置数组，shape (N, 2)
            padding: 边距比例（0.1 = 10%）
        """
        if len(positions) == 0:
            return
        
        # 计算包围盒
        min_pos = positions.min(axis=0)
        max_pos = positions.max(axis=0)
        
        # 中心
        self.center_x = (min_pos[0] + max_pos[0]) / 2.0
        self.center_y = (min_pos[1] + max_pos[1]) / 2.0
        
        # 计算合适的缩放
        world_width = max_pos[0] - min_pos[0]
        world_height = max_pos[1] - min_pos[1]
        
        if world_width < 1e-6 and world_height < 1e-6:
            # 所有点重合，使用默认缩放
            self.zoom = self._default_zoom
            return
        
        # 考虑 padding
        effective_width = self.viewport_width * (1.0 - 2.0 * padding)
        effective_height = self.viewport_height * (1.0 - 2.0 * padding)
        
        zoom_x = effective_width / max(world_width, 1e-6)
        zoom_y = effective_height / max(world_height, 1e-6)
        self.zoom = min(zoom_x, zoom_y)
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom))
    
    def get_visible_world_bounds(self) -> Tuple[float, float, float, float]:
        """
        获取当前视图可见的世界坐标范围
        
        Returns:
            (min_x, min_y, max_x, max_y)
        """
        min_x, max_y = self.screen_to_world(0, 0)
        max_x, min_y = self.screen_to_world(self.viewport_width, self.viewport_height)
        return min_x, min_y, max_x, max_y
