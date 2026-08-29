"""
模拟单位系统模块

定义 Simulation Units（模拟单位）和 UnitConverter（单位转换器）。

Physics Engine 内部只使用模拟单位：
    G  = 1
    MU = 1（质量单位）
    DU = 1（距离单位）
    TU = 1（时间单位）

导出单位由基本单位自洽推导：
    速度单位 VU = DU / TU = sqrt(G * MU / DU)
    时间单位 TU = sqrt(DU^3 / (G * MU))

UnitConverter 负责将模拟单位映射到现实世界单位（如 AU, Solar Mass, year），
但 Physics Engine 本身不依赖任何现实单位。
"""

import math
from typing import Optional, Dict


# ============================================================
# 现实世界常量（仅用于 UnitConverter，不进入物理计算）
# ============================================================

# 万有引力常数（SI 单位：m^3 kg^-1 s^-2）
G_REAL_SI = 6.67430e-11

# 天文单位（米）
AU_IN_METERS = 1.496e11

# 太阳质量（千克）
SOLAR_MASS_IN_KG = 1.989e30

# 一年（秒）
YEAR_IN_SECONDS = 3.156e7

# 一天（秒）
DAY_IN_SECONDS = 86400.0


class UnitSystem:
    """
    模拟单位系统
    
    定义基本单位 MU, DU, TU，并推导导出单位。
    在模拟单位中 G=1，因此三个基本单位不是独立的：
        TU = sqrt(DU^3 / (G * MU))
    
    一旦选定 MU 和 DU，TU 和 VU 就自动确定。
    """
    
    def __init__(
        self,
        mass_unit: str = "MU",
        distance_unit: str = "DU",
        G_value: float = 1.0
    ):
        """
        初始化模拟单位系统
        
        Args:
            mass_unit: 质量单位名称（显示用）
            distance_unit: 距离单位名称（显示用）
            G_value: 模拟中的引力常数值（默认 1.0）
        """
        self.mass_unit = mass_unit          # 质量单位名称
        self.distance_unit = distance_unit  # 距离单位名称
        self.G_value = G_value              # 模拟中的 G 值
    
    @property
    def time_unit(self) -> str:
        """时间单位名称（由基本单位导出）"""
        return "TU"
    
    @property
    def velocity_unit(self) -> str:
        """速度单位名称（由基本单位导出）"""
        return f"{self.distance_unit}/{self.time_unit}"
    
    def derived_time_unit(self) -> float:
        """
        计算导出时间单位 TU（数值上等于 1，但提供显式接口）
        
        TU = sqrt(DU^3 / (G * MU))
        在模拟单位中 DU=1, MU=1, G=1，所以 TU=1
        
        Returns:
            时间单位的数值（始终为 1.0）
        """
        return math.sqrt(1.0 ** 3 / (self.G_value * 1.0))
    
    def derived_velocity_unit(self) -> float:
        """
        计算导出速度单位 VU
        
        VU = DU / TU = sqrt(G * MU / DU)
        在模拟单位中 G=1, MU=1, DU=1，所以 VU=1
        
        Returns:
            速度单位的数值（始终为 1.0）
        """
        return math.sqrt(self.G_value * 1.0 / 1.0)
    
    def circular_orbital_velocity(self, central_mass: float, distance: float) -> float:
        """
        计算圆轨道速度（模拟单位）
        
        v = sqrt(G * M / r)
        
        Args:
            central_mass: 中心天体质量 (MU)
            distance: 轨道半径 (DU)
            
        Returns:
            圆轨道速度 (DU/TU)
        """
        return math.sqrt(self.G_value * central_mass / distance)
    
    def orbital_period(self, central_mass: float, distance: float) -> float:
        """
        计算圆轨道周期（模拟单位）
        
        T = 2 * pi * sqrt(r^3 / (G * M))
        
        Args:
            central_mass: 中心天体质量 (MU)
            distance: 轨道半径 (DU)
            
        Returns:
            轨道周期 (TU)
        """
        return 2.0 * math.pi * math.sqrt(distance ** 3 / (self.G_value * central_mass))
    
    def format_mass(self, value: float, precision: int = 2) -> str:
        """格式化质量显示"""
        return f"{value:.{precision}f} {self.mass_unit}"
    
    def format_distance(self, value: float, precision: int = 2) -> str:
        """格式化距离显示"""
        return f"{value:.{precision}f} {self.distance_unit}"
    
    def format_velocity(self, value: float, precision: int = 2) -> str:
        """格式化速度显示"""
        return f"{value:.{precision}f} {self.velocity_unit}"
    
    def format_time(self, value: float, precision: int = 2) -> str:
        """格式化时间显示"""
        return f"{value:.{precision}f} {self.time_unit}"


class UnitConverter:
    """
    单位转换器
    
    将模拟单位映射到现实世界单位。
    
    用户指定：
        1 DU = real_distance_per_DU（例如 1 AU = 1.496e11 m）
        1 MU = real_mass_per_MU（例如 1 Solar Mass = 1.989e30 kg）
    
    自动推导：
        1 TU = sqrt(DU^3 / (G_real * MU))（秒）
        1 VU = DU / TU（米/秒）
    
    注意：此转换器仅用于显示和输入转换，
    Physics Engine 内部始终使用模拟单位。
    """
    
    def __init__(
        self,
        real_distance_per_DU: float = 1.0,
        real_mass_per_MU: float = 1.0,
        real_distance_unit: str = "m",
        real_mass_unit: str = "kg",
        real_time_unit: str = "s",
        G_real: float = G_REAL_SI
    ):
        """
        初始化单位转换器
        
        Args:
            real_distance_per_DU: 1 DU 对应的现实距离（米）
            real_mass_per_MU: 1 MU 对应的现实质量（千克）
            real_distance_unit: 现实距离单位名称（显示用）
            real_mass_unit: 现实质量单位名称（显示用）
            real_time_unit: 现实时间单位名称（显示用）
            G_real: 现实万有引力常数（SI 单位）
        """
        self.real_distance_per_DU = real_distance_per_DU
        self.real_mass_per_MU = real_mass_per_MU
        self.real_distance_unit = real_distance_unit
        self.real_mass_unit = real_mass_unit
        self.real_time_unit = real_time_unit
        self.G_real = G_real
        
        # 推导现实时间单位：TU_real = sqrt(DU_real^3 / (G_real * MU_real))
        self._real_time_per_TU = math.sqrt(
            real_distance_per_DU ** 3 / (G_real * real_mass_per_MU)
        )
        
        # 推导现实速度单位：VU_real = DU_real / TU_real
        self._real_velocity_per_VU = real_distance_per_DU / self._real_time_per_TU
    
    @property
    def real_time_per_TU(self) -> float:
        """1 TU 对应的现实时间（秒）"""
        return self._real_time_per_TU
    
    @property
    def real_velocity_per_VU(self) -> float:
        """1 DU/TU 对应的现实速度（米/秒）"""
        return self._real_velocity_per_VU
    
    # ============================================================
    # 模拟单位 -> 现实单位
    # ============================================================
    
    def sim_to_real_distance(self, sim_du: float) -> float:
        """模拟距离 (DU) -> 现实距离（米）"""
        return sim_du * self.real_distance_per_DU
    
    def sim_to_real_mass(self, sim_mu: float) -> float:
        """模拟质量 (MU) -> 现实质量（千克）"""
        return sim_mu * self.real_mass_per_MU
    
    def sim_to_real_time(self, sim_tu: float) -> float:
        """模拟时间 (TU) -> 现实时间（秒）"""
        return sim_tu * self._real_time_per_TU
    
    def sim_to_real_velocity(self, sim_vu: float) -> float:
        """模拟速度 (DU/TU) -> 现实速度（米/秒）"""
        return sim_vu * self._real_velocity_per_VU
    
    # ============================================================
    # 现实单位 -> 模拟单位
    # ============================================================
    
    def real_to_sim_distance(self, real_meters: float) -> float:
        """现实距离（米）-> 模拟距离 (DU)"""
        return real_meters / self.real_distance_per_DU
    
    def real_to_sim_mass(self, real_kg: float) -> float:
        """现实质量（千克）-> 模拟质量 (MU)"""
        return real_kg / self.real_mass_per_MU
    
    def real_to_sim_time(self, real_seconds: float) -> float:
        """现实时间（秒）-> 模拟时间 (TU)"""
        return real_seconds / self._real_time_per_TU
    
    def real_to_sim_velocity(self, real_m_per_s: float) -> float:
        """现实速度（米/秒）-> 模拟速度 (DU/TU)"""
        return real_m_per_s / self._real_velocity_per_VU
    
    # ============================================================
    # 便捷工厂方法
    # ============================================================
    
    @classmethod
    def solar_system(cls) -> 'UnitConverter':
        """
        创建太阳系尺度的单位转换器
        
        1 DU = 1 AU
        1 MU = 1 Solar Mass
        
        自动推导：
        1 TU = 约 0.112 年（约 41 天）
        1 VU = 约 29.8 km/s（接近地球轨道速度）
        """
        return cls(
            real_distance_per_DU=AU_IN_METERS,
            real_mass_per_MU=SOLAR_MASS_IN_KG,
            real_distance_unit="AU",
            real_mass_unit="Solar Mass",
            real_time_unit="year"
        )
    
    def format_real_time(self, sim_tu: float) -> str:
        """
        将模拟时间格式化为现实时间字符串
        
        Args:
            sim_tu: 模拟时间 (TU)
            
        Returns:
            格式化字符串
        """
        real_seconds = self.sim_to_real_time(sim_tu)
        
        # 根据量级选择合适的显示单位
        if real_seconds > YEAR_IN_SECONDS:
            years = real_seconds / YEAR_IN_SECONDS
            return f"{years:.3f} years"
        elif real_seconds > DAY_IN_SECONDS:
            days = real_seconds / DAY_IN_SECONDS
            return f"{days:.2f} days"
        else:
            return f"{real_seconds:.2f} s"


# ============================================================
# 默认模拟单位实例
# ============================================================

# 全局默认模拟单位系统
DEFAULT_UNITS = UnitSystem()
