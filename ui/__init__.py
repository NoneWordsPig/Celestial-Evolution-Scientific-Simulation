"""
UI 模块

天体科学模拟器界面组件：
- StartupWindow：主界面（导入预设 / 新设置）
- PresetSetupDialog / NewSetupDialog：参数输入
- SimulationProgressDialog：模拟进度
- PlaybackWindow / PlaybackWidget：渲染帧回放
- AddBodyDialog / BodyListWidget / InspectorWidget / ControlPanel：复用自
  Celestial Evolution Simulation 的天体输入与信息展示组件
"""

from .add_body_dialog import AddBodyDialog
from .body_list_widget import BodyListWidget
from .inspector_widget import InspectorWidget
from .control_panel import ControlPanel
from .scientific_number_input import ScientificNumberInput
from .playback_widget import PlaybackWidget
from .playback_window import PlaybackWindow
from .simulation_progress_dialog import SimulationProgressDialog
from .setup_dialogs import PresetSetupDialog, NewSetupDialog
from .startup_window import StartupWindow

__all__ = [
    'AddBodyDialog',
    'BodyListWidget',
    'InspectorWidget',
    'ControlPanel',
    'ScientificNumberInput',
    'PlaybackWidget',
    'PlaybackWindow',
    'SimulationProgressDialog',
    'PresetSetupDialog',
    'NewSetupDialog',
    'StartupWindow',
]
