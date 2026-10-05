# Celestial Evolution Scientific Simulation · 天体科学模拟器

> 离线 N 体引力科学模拟器。物理模块与大部分 UI 复制自 Celestial Evolution Simulation，
> 但以"按时间步长直接模拟 → 显示模拟进度 → 60 FPS 回放渲染帧"的工作流取代实时渲染。

## 工作流程

1. 进入主界面后直接显示两个选项模块：**导入预设** / **新设置**。
2. **导入预设**：选择 Celestial Evolution Simulation 的预设（`scenes/*.json`），
   仅需输入三个参数：模拟时长、模拟时间步长、播放速度。
3. **新设置**：先输入星体数，再逐个输入每个天体的位置、大小、质量、速度等
   （输入方法同 Celestial Evolution Simulation 的 AddBodyDialog，支持模拟单位
   DU/MU/TU 与科学单位 m/kg/AU/s），最后输入三个模拟参数。
4. 输入完毕后按时间步长直接模拟，**不渲染**，实时显示**模拟进度**
   （进度条、已计算步数/总步数、已用时间、预计剩余时间，可取消）。
5. 模拟完成后，按 60 帧/秒回放记录的渲染帧，可播放/暂停/重播/拖动进度；
   回放视图支持滚轮缩放、左键拖动平移、双击复位，渲染采用等比缩放保证轨道形状不变形。

## 存储策略（考虑计算开销）

- 每个时间步只保留当前时刻每个星体的**位置/速度**用于下一步计算；
- 仅在**渲染帧**处完整储存星体位置等快照：每 `播放速度 / 60` 个时间单位一帧
  （播放速度为 1 时每秒渲染经过 1 标准时间，帧率 60 帧/秒）。

例：模拟时长 100、时间步长 0.0000001、播放速度 1，则共进行 `100 / 1e-7 = 10^9`
次物理步，但只储存约 `100 × 60 = 6000` 个渲染帧的位置快照。

## 计算精度

- **自动检测**：解析所有输入数值（位置、速度、质量、半径等）的原始文本；
  若均能被 float64 无损表示（"输入精度较小时"），使用常规 **16 位精度**
  （float64 快速路径：安装 numba 时使用融合 JIT 内核，RK4 与碰撞检测一次
  完成、无临时数组分配；未安装时自动回退 NumPy 向量化 RK4）；
- 若任一输入有效位数超出 float64（约 16 位）范围，自动切换 **Decimal 高精度**
  路径（默认 ≥50 位有效数字，可支持超过 20 位），同样使用 RK4；
- 也可在参数中显式指定"计算精度（有效位数）"强制使用高精度模式。

物理引擎与 Celestial Evolution Simulation 一致：G=1、归一化模拟单位、
RK4（与预设积分器相同）、碰撞检测与融合、软化因子。

## 默认参数

| 参数 | 默认值 |
| --- | --- |
| 模拟时间步长 | 0.0001 TU |
| 模拟时长 | 60 TU |
| 播放速度 | 1 TU/s（60 帧/秒） |
| 星体数（新设置） | 3 |
| 计算精度 | 自动 |

其他默认（天体输入默认值、预设内容等）同 Celestial Evolution Simulation。

## Windows 下载（0.1）

前往 [GitHub Release 0.1](https://github.com/NoneWordsPig/Celestial-Evolution-Scientific-Simulation/releases/tag/0.1)，下载 `Celestial-Evolution-Scientific-Simulation-0.1-Windows-x64.exe`，双击即可运行，无需安装 Python。

- 适用于 Windows 10/11 64 位，内置 9 个预设、PyQt6、NumPy 和 Numba。
- 首次启动需要解压内置依赖；首次模拟需要编译 JIT 内核，请稍候。
- 选择“导入预设”或“新设置”，设置模拟时长、步长与播放速度，计算完成后进入回放。
- Release 附带 `SHA256SUMS.txt`，可用 PowerShell 的 `Get-FileHash -Algorithm SHA256` 校验下载文件。

## 源码安装与运行

```bash
pip install -r requirements.txt   # numba 可选但强烈推荐：float64 路径可加速计算，实际效果取决于场景和运行环境
python main.py
```

## 构建 Windows EXE

在 Windows 上进入项目根目录，安装依赖后执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller ui/packaging/release.spec --distpath ui/packaging/dist --workpath ui/packaging/build --noconfirm
```

输出位于 `ui/packaging/dist/`，为包含预设和依赖的单文件程序。打包配置保留 Numba 内核源码以支持冻结程序中的 JIT 缓存。

运行现有物理回归测试：

```powershell
python -m unittest discover -s tests -v
```

## 使用提示

- 计算总步数约为 `模拟时长 / 时间步长`；减小步长会显著增加计算时间。
- 回放帧数约为 `模拟时长 / 播放速度 × 60`；帧快照保存在内存中，长时模拟需考虑内存容量。
- 60 FPS 为目标回放帧率，实际效果取决于设备性能与天体数量。
- 高精度模式可减少数值表示误差，但运行更慢；积分误差仍取决于步长与算法。

## 项目结构

```
main.py                         # 入口：主界面显示"导入预设/新设置"
physics/                        # 全部物理模块（复制自 Celestial Evolution Simulation）
scenes/                         # 预设（复制自 Celestial Evolution Simulation）
scientific/
  precision.py                  # 高精度解析 / 精度检测 / Decimal 单位换算
  simulator.py                  # 批量离线模拟器（float64 + Decimal 双路径）
  worker.py                     # Qt 后台线程
ui/
  startup_window.py             # 主界面
  setup_dialogs.py              # 导入预设 / 新设置对话框
  simulation_progress_dialog.py # 模拟进度
  playback_widget.py            # 回放渲染组件
  playback_window.py            # 回放窗口
  add_body_dialog.py            # 天体输入（同 Celestial Evolution Simulation）
  scientific_number_input.py    # 科学计数输入控件
  body_list_widget.py           # 天体列表
  inspector_widget.py           # 天体检查器
  control_panel.py              # 控制面板
  styles.py                     # 深色宇宙主题
  toast.py                      # 提示气泡
```

## 说明

- 本项目的物理模块与大部分 UI 复制自 Celestial Evolution Simulation；
  原项目未做任何修改。
- 高精度路径中，极坐标速度（速率+角度）的三角函数使用标准库 `math`
  （float 精度）；需要完整精度的速度输入请使用 X/Y 笛卡尔模式。
