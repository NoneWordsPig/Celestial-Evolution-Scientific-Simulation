"""
动画过渡系统

提供平滑的摄像机移动和动量修正过渡
使用 cubic easing 缓动函数
"""

import numpy as np
from typing import Callable, Optional
from .camera import Camera
from .body import Body


def ease_in_out_cubic(t: float) -> float:
    """
    三次缓入缓出函数
    
    t < 0.5: 4 * t^3
    t >= 0.5: 1 - (-2*t + 2)^3 / 2
    
    Args:
        t: 进度 [0, 1]
        
    Returns:
        缓动后的值 [0, 1]
    """
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        return 1.0 - pow(-2.0 * t + 2.0, 3) / 2.0


def lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    """
    线性插值
    
    Args:
        a: 起始值
        b: 目标值
        t: 进度 [0, 1]
        
    Returns:
        插值结果
    """
    return a + (b - a) * t


class Transition:
    """
    基础过渡类
    """
    
    def __init__(self, duration: float = 1.0):
        """
        初始化过渡
        
        Args:
            duration: 过渡持续时间（秒）
        """
        self.duration = duration
        self.elapsed = 0.0
        self.is_active = False
        self.easing_func = ease_in_out_cubic
    
    def start(self) -> None:
        """开始过渡"""
        self.elapsed = 0.0
        self.is_active = True
    
    def update(self, dt: float) -> bool:
        """
        更新过渡进度
        
        Args:
            dt: 时间步长（秒）
            
        Returns:
            是否仍在进行中
        """
        if not self.is_active:
            return False
        
        self.elapsed += dt
        
        if self.elapsed >= self.duration:
            self.is_active = False
            return False
        
        return True
    
    def get_progress(self) -> float:
        """
        获取当前进度
        
        Returns:
            进度 [0, 1]
        """
        if not self.is_active:
            return 1.0
        
        return min(1.0, self.elapsed / self.duration)
    
    def get_eased_progress(self) -> float:
        """
        获取缓动后的进度
        
        Returns:
            缓动后的进度 [0, 1]
        """
        return self.easing_func(self.get_progress())


class CameraTransition(Transition):
    """
    摄像机平滑过渡
    
    将摄像机从当前位置平滑移动到目标位置
    """
    
    def __init__(
        self,
        camera: Camera,
        target_center: np.ndarray,
        duration: float = 0.8,
        threshold: float = 0.1
    ):
        """
        初始化摄像机过渡
        
        Args:
            camera: 摄像机对象
            target_center: 目标中心位置
            duration: 过渡持续时间（秒）
            threshold: 距离阈值，小于此值时直接跳转
        """
        super().__init__(duration)
        self.camera = camera
        self.target_center = target_center.copy()
        self.threshold = threshold
        
        self.start_center = None
        self._distance = 0.0
    
    def start(self) -> None:
        """开始过渡"""
        super().start()
        self.start_center = np.array([self.camera.center_x, self.camera.center_y])
        
        # 计算距离
        self._distance = np.linalg.norm(self.target_center - self.start_center)
        
        # 如果距离小于阈值，直接跳转
        if self._distance < self.threshold:
            self.camera.center_x = self.target_center[0]
            self.camera.center_y = self.target_center[1]
            self.is_active = False
    
    def update(self, dt: float) -> bool:
        """
        更新过渡
        
        Args:
            dt: 时间步长（秒）
            
        Returns:
            是否仍在进行中
        """
        if not super().update(dt):
            return False
        
        # 应用缓动
        t = self.get_eased_progress()
        
        # 插值位置
        new_center = lerp(self.start_center, self.target_center, t)
        
        # 更新摄像机
        self.camera.center_x = new_center[0]
        self.camera.center_y = new_center[1]
        
        return True
    
    @property
    def distance(self) -> float:
        """获取过渡距离"""
        return self._distance


class MomentumCorrectionTransition(Transition):
    """
    动量修正过渡
    
    平滑地将系统总动量修正为零
    """
    
    def __init__(
        self,
        bodies: list,
        velocity_offset: np.ndarray,
        duration: float = 1.0
    ):
        """
        初始化动量修正过渡
        
        Args:
            bodies: 天体列表
            velocity_offset: 需要减去的速度偏移（V_cm）
            duration: 过渡持续时间（秒）
        """
        super().__init__(duration)
        self.bodies = bodies
        # 我们要从速度中减去 velocity_offset
        # 过渡从 offset=0 开始，逐渐增加到 offset=velocity_offset
        self.target_offset = velocity_offset.copy()
        
        # 保存初始速度
        self.initial_velocities = [b.velocity.copy() for b in bodies]
        self._last_applied_offset = np.array([0.0, 0.0])
    
    def start(self) -> None:
        """开始过渡"""
        super().start()
        # 重新保存初始速度
        self.initial_velocities = [b.velocity.copy() for b in self.bodies]
        self._last_applied_offset = np.array([0.0, 0.0])
    
    def update(self, dt: float) -> bool:
        """
        更新过渡
        
        Args:
            dt: 时间步长（秒）
            
        Returns:
            是否仍在进行中
        """
        if not self.is_active:
            return False
        
        self.elapsed += dt
        
        # 计算当前进度
        if self.elapsed >= self.duration:
            # 过渡完成
            self.is_active = False
            t = 1.0
        else:
            t = self.get_eased_progress()
        
        # 计算当前应该应用的偏移（从 0 到 target_offset）
        start_offset = np.array([0.0, 0.0])
        current_offset = lerp(start_offset, self.target_offset, t)
        
        # 计算偏移变化量
        delta_offset = current_offset - self._last_applied_offset
        
        # 应用偏移变化量到所有天体（减去偏移）
        for body in self.bodies:
            body.velocity -= delta_offset
        
        # 记录已应用的偏移
        self._last_applied_offset = current_offset
        
        return self.is_active
    
    @property
    def current_offset(self) -> np.ndarray:
        """获取当前已应用的速度偏移"""
        return self._last_applied_offset.copy()


class TransitionManager:
    """
    过渡管理器
    
    管理多个同时进行的过渡
    """
    
    def __init__(self):
        """初始化过渡管理器"""
        self.camera_transition: Optional[CameraTransition] = None
        self.momentum_transition: Optional[MomentumCorrectionTransition] = None
    
    def start_camera_transition(
        self,
        camera: Camera,
        target_center: np.ndarray,
        duration: float = 0.8,
        threshold: float = 0.1
    ) -> None:
        """
        启动摄像机过渡
        
        Args:
            camera: 摄像机对象
            target_center: 目标中心位置
            duration: 过渡持续时间（秒）
            threshold: 距离阈值
        """
        self.camera_transition = CameraTransition(
            camera, target_center, duration, threshold
        )
        self.camera_transition.start()
    
    def start_momentum_correction(
        self,
        bodies: list,
        velocity_offset: np.ndarray,
        duration: float = 1.0
    ) -> None:
        """
        启动动量修正过渡
        
        Args:
            bodies: 天体列表
            velocity_offset: 初始速度偏移
            duration: 过渡持续时间（秒）
        """
        self.momentum_transition = MomentumCorrectionTransition(
            bodies, velocity_offset, duration
        )
        self.momentum_transition.start()
    
    def update(self, dt: float) -> None:
        """
        更新所有过渡
        
        Args:
            dt: 时间步长（秒）
        """
        if self.camera_transition and self.camera_transition.is_active:
            self.camera_transition.update(dt)
        
        if self.momentum_transition and self.momentum_transition.is_active:
            self.momentum_transition.update(dt)
    
    @property
    def is_camera_transition_active(self) -> bool:
        """摄像机过渡是否活跃"""
        return self.camera_transition is not None and self.camera_transition.is_active
    
    @property
    def is_momentum_transition_active(self) -> bool:
        """动量修正过渡是否活跃"""
        return self.momentum_transition is not None and self.momentum_transition.is_active
    
    @property
    def is_any_transition_active(self) -> bool:
        """是否有任何过渡活跃"""
        return self.is_camera_transition_active or self.is_momentum_transition_active
