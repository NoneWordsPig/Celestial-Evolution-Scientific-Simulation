"""
独立 SceneManager 模块

负责 Scene 的 JSON 读写：
- Save Scene：将当前引擎/相机状态序列化并保存为 JSON
- Load Scene：从 JSON 读取 Scene
- Import Scene：读取 JSON 并应用到当前引擎/相机
- Export Scene：将当前引擎/相机状态导出为 JSON 文件

所有场景统一使用 JSON Scene 文件（Example Scene 与 User Scene 格式完全相同），
程序启动时自动扫描 scenes/ 目录，目录内所有 JSON 都视为普通 Scene。

SceneManager 只负责数据序列化与文件读写，不进行任何物理计算；
PhysicsEngine 不负责文件读写。
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .body import Body
from .integrator import IntegratorFactory


FORMAT_VERSION = 1

# 场景默认单位元数据（仅记录用途，SceneManager 不做单位换算）
DEFAULT_UNITS = {
    "length": "AU",
    "mass": "M_sun",
    "time": "TU",
    "velocity": "DU/TU",
}

# 积分器类名 -> Scene JSON 中的键
_INTEGRATOR_KEYS = {
    'VelocityVerletIntegrator': 'verlet',
    'RK4Integrator': 'rk4',
}


class SceneManager:
    """
    场景管理器：JSON 读写，不进行物理计算

    依赖对象只需提供下列属性（duck typing）：
    - engine: bodies, dt, time_scale, simulation_time, integrator
    - body: name, mass, physical_radius, render_radius, position, velocity, color
    - camera: center_x, center_y, zoom, viewport_width, viewport_height
    """

    def __init__(self, scenes_directory: Optional[str] = None):
        # 默认 scenes/ 位于项目根目录
        root = Path(__file__).resolve().parent.parent
        self.scenes_directory = (
            Path(scenes_directory) if scenes_directory else root / 'scenes'
        )

    # ============================================================
    # 序列化（不进行物理计算）
    # ============================================================

    def scene_to_dict(
        self,
        engine,
        camera,
        name: str = "",
        description: str = "",
        units: Optional[Dict] = None,
    ) -> dict:
        """将引擎/相机状态序列化为 Scene dict"""
        return {
            "format_version": FORMAT_VERSION,
            "name": name,
            "description": description,
            "units": dict(units) if units is not None else dict(DEFAULT_UNITS),
            "G": 1.0,
            "integrator": self._integrator_key(engine),
            "timestep": float(engine.dt),
            "time_scale": float(engine.time_scale),
            "simulation_time": float(engine.simulation_time),
            "camera": {
                "center_x": float(camera.center_x),
                "center_y": float(camera.center_y),
                "zoom": float(camera.zoom),
                "viewport_width": int(camera.viewport_width),
                "viewport_height": int(camera.viewport_height),
            },
            "bodies": [self._body_to_dict(b) for b in engine.bodies],
        }

    def _body_to_dict(self, body) -> dict:
        """单个天体 -> dict"""
        return {
            "name": body.name,
            "mass": float(body.mass),
            "radius": float(body.physical_radius),
            "render_radius": float(body.render_radius),
            "position": [float(body.position[0]), float(body.position[1])],
            "velocity": [float(body.velocity[0]), float(body.velocity[1])],
            "color": [
                float(body.color[0]),
                float(body.color[1]),
                float(body.color[2]),
            ],
        }

    def _integrator_key(self, engine) -> str:
        """从积分器实例推断 Scene 键名"""
        return _INTEGRATOR_KEYS.get(type(engine.integrator).__name__, 'rk4')

    # ============================================================
    # 反序列化（不进行物理计算）
    # ============================================================

    def dict_to_scene(self, scene: dict, engine, camera) -> dict:
        """将 Scene dict 应用到引擎/相机"""
        engine.clear()

        # 引擎参数
        engine.dt = float(scene.get('timestep', engine.dt))
        engine.time_scale = float(scene.get('time_scale', engine.time_scale))
        engine.simulation_time = float(scene.get('simulation_time', 0.0))
        engine.integrator = IntegratorFactory.create(
            scene.get('integrator', 'rk4'), engine.gravity_solver
        )
        engine._cached_accelerations = None

        # 天体
        for b in scene.get('bodies', []):
            engine.add_body(self._body_from_dict(b))

        # 相机
        cam = scene.get('camera', {})
        camera.center_x = float(cam.get('center_x', camera.center_x))
        camera.center_y = float(cam.get('center_y', camera.center_y))
        camera.zoom = float(cam.get('zoom', camera.zoom))
        camera.viewport_width = int(cam.get('viewport_width', camera.viewport_width))
        camera.viewport_height = int(cam.get('viewport_height', camera.viewport_height))

        return scene

    def _body_from_dict(self, data: dict) -> Body:
        """dict -> Body"""
        color = data.get('color')
        if color is not None:
            color = (float(color[0]), float(color[1]), float(color[2]))
        else:
            color = (1.0, 1.0, 1.0)

        render_radius = data.get('render_radius')

        return Body(
            name=data.get('name', 'Body'),
            mass=float(data.get('mass', 1.0)),
            physical_radius=float(data.get('radius', 1.0)),
            render_radius=(
                float(render_radius) if render_radius is not None else None
            ),
            position=(
                float(data['position'][0]),
                float(data['position'][1]),
            ),
            velocity=(
                float(data['velocity'][0]),
                float(data['velocity'][1]),
            ),
            color=color,
        )

    # ============================================================
    # Save / Load / Import / Export
    # ============================================================

    def save_scene(self, scene: dict, path) -> str:
        """保存 Scene dict 为 JSON 文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(scene, f, indent=2, ensure_ascii=False)
        return str(path)

    def load_scene(self, path) -> dict:
        """读取 JSON 文件为 Scene dict"""
        with open(path, 'r', encoding='utf-8') as f:
            scene = json.load(f)
        if not isinstance(scene, dict):
            raise ValueError(f"Scene 必须是 JSON 对象: {path}")
        return scene

    def import_scene(self, path, engine, camera) -> dict:
        """读取 JSON 并应用到当前引擎/相机"""
        scene = self.load_scene(path)
        self.dict_to_scene(scene, engine, camera)
        return scene

    def export_scene(
        self,
        engine,
        camera,
        path,
        name: str = "",
        description: str = "",
        units: Optional[Dict] = None,
    ) -> str:
        """将当前引擎/相机状态导出为 JSON 文件"""
        scene = self.scene_to_dict(
            engine, camera, name=name, description=description, units=units
        )
        return self.save_scene(scene, path)

    # ============================================================
    # 启动扫描
    # ============================================================

    def scan_scenes(self, directory: Optional[str] = None) -> List[dict]:
        """
        扫描 scenes 目录下所有 JSON，返回场景信息列表。

        目录内所有 .json 都视为普通 Scene；无法解析的文件被跳过。
        """
        directory = Path(directory) if directory else self.scenes_directory
        if not directory.is_dir():
            return []

        scenes = []
        for path in sorted(directory.glob('*.json')):
            try:
                scene = self.load_scene(path)
            except (json.JSONDecodeError, ValueError, OSError):
                continue
            scenes.append({
                'path': str(path),
                'name': scene.get('name', path.stem),
                'description': scene.get('description', ''),
            })
        return scenes
