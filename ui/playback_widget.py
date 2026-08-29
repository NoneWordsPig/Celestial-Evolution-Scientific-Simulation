"""
回放渲染组件（QPainter 2D）

将科学模拟记录的"渲染帧"按 60 FPS 回放：
- 深色宇宙背景 + 参考网格
- 天体按颜色绘制为圆（物理半径映射，带最小像素尺寸）
- 最近若干帧轨迹
- 当前时间显示

视图控制：
- 滚轮：以鼠标位置为中心缩放
- 左键拖动：平移地图
- 双击：复位视图

渲染采用等比缩放（X/Y 每世界单位像素数一致），保证轨道、圆形天体
不会被拉伸变形（例如太阳系轨道保持正圆）。
"""

import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF

from scientific.simulator import SimulationResult


class PlaybackWidget(QWidget):
    """渲染帧回放组件（支持缩放 / 平移 / 复位）"""

    TRAIL_FRAMES = 200

    def __init__(self, result: SimulationResult, parent=None):
        super().__init__(parent)
        self._result = result
        self._frame_index = 0

        # 视图状态：中心世界坐标 + 每世界单位像素数（等比）
        self._center = (0.0, 0.0)
        self._scale = 1.0
        self._base_bounds = self._compute_bounds()
        self._min_scale = None
        self._max_scale = None
        self._panning = False
        self._last_mouse = None
        self.setMinimumSize(400, 300)
        self._reset_view()

    # ---- 视图控制 ----
    def _reset_view(self):
        min_x, max_x, min_y, max_y = self._base_bounds
        self._center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
        span_x = max(max_x - min_x, 1e-9)
        span_y = max(max_y - min_y, 1e-9)
        base_scale = min(self.width() / span_x, self.height() / span_y) * 0.95
        if base_scale <= 0:
            base_scale = 1.0
        self._scale = base_scale
        self._min_scale = base_scale * 0.02
        self._max_scale = base_scale * 1e6
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        pos = event.position()
        # 缩放前鼠标下的世界坐标
        wx, wy = self._screen_to_world(pos)
        new_scale = min(max(self._scale * factor, self._min_scale), self._max_scale)
        self._scale = new_scale
        # 缩放后仍让 (wx, wy) 位于鼠标位置
        cx, cy = self._center
        w, h = self.width(), self.height()
        self._center = (
            wx - (pos.x() - w / 2.0) / self._scale,
            wy + (pos.y() - h / 2.0) / self._scale,
        )
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._last_mouse = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._panning and self._last_mouse is not None:
            pos = event.position()
            dx = pos.x() - self._last_mouse.x()
            dy = pos.y() - self._last_mouse.y()
            cx, cy = self._center
            self._center = (cx - dx / self._scale, cy + dy / self._scale)
            self._last_mouse = pos
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self._last_mouse = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._reset_view()

    # ---- 坐标变换（等比缩放，不拉伸） ----
    def _screen_to_world(self, pos):
        cx, cy = self._center
        w, h = self.width(), self.height()
        return (
            cx + (pos.x() - w / 2.0) / self._scale,
            cy - (pos.y() - h / 2.0) / self._scale,
        )

    def _to_screen(self, x: float, y: float):
        cx, cy = self._center
        w, h = self.width(), self.height()
        return (
            w / 2.0 + (x - cx) * self._scale,
            h / 2.0 - (y - cy) * self._scale,
        )

    # ---- 帧控制 ----
    def set_frame(self, index: int):
        self._frame_index = max(0, min(index, self._result.frame_count - 1))
        self.update()

    def current_frame(self) -> int:
        return self._frame_index

    def frame_time(self) -> float:
        idx = min(self._frame_index, len(self._result.frame_times) - 1)
        return self._result.frame_times[idx] if idx >= 0 else 0.0

    # ---- 视图 ----
    def _compute_bounds(self):
        """计算所有渲染帧的包围盒（含边距）。"""
        xs, ys = [], []
        for frame in self._result.frame_positions:
            for (x, y) in frame:
                try:
                    xs.append(float(x))
                    ys.append(float(y))
                except (TypeError, ValueError):
                    continue
        if not xs:
            return (-10.0, 10.0, -10.0, 10.0)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)
        pad = 0.08 * max(span_x, span_y)
        return (min_x - pad, max_x + pad, min_y - pad, max_y + pad)

    # ---- 绘制 ----
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor(10, 14, 26))

        self._draw_grid(painter)
        self._draw_trails(painter)
        self._draw_bodies(painter)
        self._draw_overlay(painter)

        painter.end()

    def _draw_grid(self, painter: QPainter):
        min_x, max_x, min_y, max_y = self._view_world_bounds()
        pen = QPen(QColor(45, 51, 72, 120))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        # 8x8 网格
        for i in range(9):
            t = i / 8.0
            x = min_x + (max_x - min_x) * t
            sx, _ = self._to_screen(x, min_y)
            painter.drawLine(int(sx), 0, int(sx), self.height())
            y = min_y + (max_y - min_y) * t
            _, sy = self._to_screen(min_x, y)
            painter.drawLine(0, int(sy), self.width(), int(sy))
        # 坐标轴（近似经过原点）
        pen2 = QPen(QColor(99, 102, 241, 160))
        pen2.setWidthF(1.2)
        painter.setPen(pen2)
        ox, oy = self._to_screen(0.0, 0.0)
        if 0 <= ox <= self.width():
            painter.drawLine(int(ox), 0, int(ox), self.height())
        if 0 <= oy <= self.height():
            painter.drawLine(0, int(oy), self.width(), int(oy))

    def _view_world_bounds(self):
        """当前视图对应的世界坐标范围（用于网格绘制）。"""
        w, h = self.width(), self.height()
        cx, cy = self._center
        half_w = w / (2.0 * self._scale)
        half_h = h / (2.0 * self._scale)
        return (cx - half_w, cx + half_w, cy - half_h, cy + half_h)

    def _draw_trails(self, painter: QPainter):
        result = self._result
        idx = self._frame_index
        if idx <= 0:
            return
        start = max(0, idx - self.TRAIL_FRAMES)
        body_count = len(result.frame_positions[idx])
        for b in range(body_count):
            pts = []
            for f in range(start, idx + 1):
                frame = result.frame_positions[f]
                if b >= len(frame):
                    continue
                try:
                    pts.append(self._to_screen(float(frame[b][0]), float(frame[b][1])))
                except (TypeError, ValueError):
                    continue
            if len(pts) < 2:
                continue
            color = self._body_color(b, idx)
            pen = QPen(QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), 110))
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF([QPointF(*p) for p in pts]))

    def _draw_bodies(self, painter: QPainter):
        result = self._result
        idx = self._frame_index
        frame = result.frame_positions[idx]
        radii = result.frame_radii[idx]
        for b, (pos, r) in enumerate(zip(frame, radii)):
            try:
                sx, sy = self._to_screen(float(pos[0]), float(pos[1]))
            except (TypeError, ValueError):
                continue
            radius_px = max(2.5, float(r) * self._scale)
            color = self._body_color(b, idx)
            qcolor = QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
            painter.setPen(QPen(qcolor.lighter(150), 1.0))
            painter.setBrush(qcolor)
            painter.drawEllipse(int(sx - radius_px), int(sy - radius_px),
                                int(radius_px * 2), int(radius_px * 2))

    def _draw_overlay(self, painter: QPainter):
        painter.setPen(QColor(156, 163, 175))
        painter.setFont(self.font())
        t = self.frame_time()
        painter.drawText(10, self.height() - 10, f"t = {t:.6f} TU")
        body_count = len(self._result.frame_positions[self._frame_index])
        painter.drawText(10, self.height() - 30, f"天体数: {body_count}")
        # 操作提示
        painter.setPen(QColor(107, 114, 128))
        painter.drawText(self.width() - 10, 14, "滚轮缩放 · 拖动平移 · 双击复位")

    def _body_color(self, body_index: int, frame_index: int):
        colors = self._result.frame_colors[frame_index]
        if body_index < len(colors):
            c = colors[body_index]
            try:
                return (float(c[0]), float(c[1]), float(c[2]))
            except (TypeError, ValueError):
                pass
        return (1.0, 1.0, 1.0)
