"""
统一的科学计数数值输入控件

支持高精度数值输入：
- 普通小数：1, 0.1, 0.000001
- 科学计数法：1e-6, 3.003e-6, 1.989e30

内部使用 float64（Python float），不做固定小数位限制。
显示时最多保留约 15 位有效数字，指数不补零（3.003e-6 而非 3.003e-06）。
"""

from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel


def format_number(value: float) -> str:
    """格式化浮点数：最多约 15 位有效数字，不使用固定小数位"""
    v = float(value)
    if v == 0.0:
        return '0'
    # 先尝试 15 位有效数字
    text = format(v, '.15g')
    # 若 15 位不足以精确往返，退回最短可逆表示（repr）
    if float(text) != v:
        text = repr(v)
    return _normalize_exponent(text)


def _normalize_exponent(text: str) -> str:
    """将 e-06 规范为 e-6、e+30 规范为 e30"""
    low = text.lower()
    if 'e' not in low:
        return text
    mantissa, _, exp = low.partition('e')
    return f"{mantissa}e{int(exp)}"


class ScientificNumberInput(QWidget):
    """统一的科学计数数值输入控件"""

    def __init__(
        self,
        value: float = 0.0,
        min_value: float = None,
        max_value: float = None,
        suffix: str = "",
        parent=None
    ):
        super().__init__(parent)
        self._min_value = None if min_value is None else float(min_value)
        self._max_value = None if max_value is None else float(max_value)
        self._last_valid = float(value)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.line_edit = QLineEdit()
        self.line_edit.setText(format_number(self._last_valid))

        # 只校验格式（科学计数法），范围由控件在读取/完成编辑时钳制，
        # 避免范围下限为正数时无法输入 "0.5" 这类中间状态。
        self._validator = QDoubleValidator()
        self._validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
        self.line_edit.setValidator(self._validator)

        self.suffix_label = QLabel(suffix)
        self.suffix_label.setStyleSheet("color: #9ca3af;")

        layout.addWidget(self.line_edit, 1)
        if suffix:
            layout.addWidget(self.suffix_label)

        # 失焦或按回车时规范显示
        self.line_edit.editingFinished.connect(self._normalize_display)

    # ---- 数值读取 ----
    def value(self) -> float:
        text = self.line_edit.text().strip()
        try:
            v = float(text)
        except ValueError:
            v = self._last_valid
        return self._clamp(v)

    # ---- 数值写入（兼容 QDoubleSpinBox 风格 API）----
    def setValue(self, v: float) -> None:
        v = self._clamp(float(v))
        self._last_valid = v
        self.line_edit.setText(format_number(v))

    set_value = setValue

    # ---- 范围 ----
    def setRange(self, minimum, maximum) -> None:
        self._min_value = None if minimum is None else float(minimum)
        self._max_value = None if maximum is None else float(maximum)

    def minimum(self):
        return self._min_value

    def maximum(self):
        return self._max_value

    # ---- 后缀 ----
    def setSuffix(self, suffix: str) -> None:
        self.suffix_label.setText(suffix)
        self.suffix_label.setVisible(bool(suffix))

    # ---- 兼容旧接口：无固定小数位，忽略 ----
    def setDecimals(self, decimals: int) -> None:
        pass


    # ---- 高精度原始文本 ----
    def raw_text(self) -> str:
        """返回输入框中的原始文本（保留用户输入的全部有效位数）。

        科学模拟使用该方法读取原始文本，以便在输入精度超过 float64
        （约 16 位）时启用高精度 Decimal 计算。
        """
        return self.line_edit.text().strip()
    # ---- 内部 ----
    def _clamp(self, v: float) -> float:
        if self._min_value is not None and v < self._min_value:
            return self._min_value
        if self._max_value is not None and v > self._max_value:
            return self._max_value
        return v

    def _normalize_display(self) -> None:
        v = self.value()
        self._last_valid = v
        self.line_edit.setText(format_number(v))

