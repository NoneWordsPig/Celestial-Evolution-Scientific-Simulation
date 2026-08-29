"""
回放渲染组件（QPainter 2D）

将科学模拟记录的"渲染帧"按 60 FPS 回放：
- 深色宇宙背景 + 参考网格
- 天体按颜色绘制为圆（物理半径映射，带最小像素尺寸）
- 最近若干帧轨迹
- 当前时间显示
"""

import math

import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPolygonF

from scientific.simulator import SimulationResult


class PlaybackWidget(QWidget):
    """渲染帧回放组件"""

    TRAIL_FRAMES = 200

    def __init__(self, result: SimulationResult, parent=None):
        super().__init__(parent)
        self._result = result
        self._frame_index = 0
        self._view_bounds = self._compute_bounds()
        self.setMinimumSize(400, 300)

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

    def _to_screen(self, x: float, y: float):
        min_x, max_x, min_y, max_y = self._view_bounds
        w, h = self.width(), self.height()
        sx = (x - min_x) / (max_x - min_x) * w
        sy = h - (y - min_y) / (max_y - min_y) * h
        return sx, sy

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
        min_x, max_x, min_y, max_y = self._view_bounds
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
        if min_x <= 0 <= max_x:
            painter.drawLine(int(ox), 0, int(ox), self.height())
        if min_y <= 0 <= max_y:
            painter.drawLine(0, int(oy), self.width(), int(oy))

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
        w, h = self.width(), self.height()
        span = max(self._view_bounds[1] - self._view_bounds[0],
                   self._view_bounds[3] - self._view_bounds[2])
        scale = min(w, h) / span
        for b, (pos, r) in enumerate(zip(frame, radii)):
            try:
                sx, sy = self._to_screen(float(pos[0]), float(pos[1]))
            except (TypeError, ValueError):
                continue
            radius_px = max(2.5, float(r) * scale)
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

    def _body_color(self, body_index: int, frame_index: int):
        colors = self._result.frame_colors[frame_index]
        if body_index < len(colors):
            c = colors[body_index]
            try:
                return (float(c[0]), float(c[1]), float(c[2]))
            except (TypeError, ValueError):
                pass
        return (1.0, 1.0, 1.0)

