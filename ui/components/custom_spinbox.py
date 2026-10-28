from PySide6.QtCore import Qt
from qfluentwidgets import DoubleSpinBox, SpinBox, DateEdit, DateTimeEdit


class CurrencySpinBox(DoubleSpinBox):
    """
    Enhanced DoubleSpinBox for currency input.
    Fixes the Qt6/QFluentWidgets lineEdit squishing bug where large amounts
    (e.g., $ 7,000,000.00) were cut off or covered by stepper buttons.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.01, 1_000_000_000.0)
        self.setDecimals(2)
        self.setPrefix("$ ")
        self.setMinimumWidth(240)
        self.setFixedHeight(36)
        self.setSymbolVisible(False)  # Currency inputs do not need 1-step buttons

    def textFromValue(self, val: float) -> str:
        return f"{val:,.2f}"

    def valueFromText(self, text: str) -> float:
        clean = text.replace("$", "").replace(",", "").strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        is_btn_visible = hasattr(self, "upButton") and not self.upButton.isHidden()
        btn_w = 68 if is_btn_visible else 0
        self.lineEdit().setGeometry(12, 2, max(60, w - btn_w - 20), h - 4)


class PercentSpinBox(DoubleSpinBox):
    """Enhanced DoubleSpinBox for percentage rates."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.0, 500.0)
        self.setDecimals(2)
        self.setSuffix(" %")
        self.setMinimumWidth(160)
        self.setFixedHeight(36)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        is_btn_visible = hasattr(self, "upButton") and not self.upButton.isHidden()
        btn_w = 68 if is_btn_visible else 0
        self.lineEdit().setGeometry(12, 2, max(50, w - btn_w - 20), h - 4)


class IntegerSpinBox(SpinBox):
    """Enhanced SpinBox for term durations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(1, 1000)
        self.setMinimumWidth(140)
        self.setFixedHeight(36)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        is_btn_visible = hasattr(self, "upButton") and not self.upButton.isHidden()
        btn_w = 68 if is_btn_visible else 0
        self.lineEdit().setGeometry(12, 2, max(40, w - btn_w - 20), h - 4)


class CustomDateEdit(DateEdit):
    """
    Enhanced DateEdit that fixes Qt6 layout bug where date text was squished
    to 1 pixel and cut off.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy")
        self.setMinimumWidth(200)
        self.setFixedHeight(36)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        is_btn_visible = hasattr(self, "upButton") and not self.upButton.isHidden()
        btn_w = 68 if is_btn_visible else 0
        self.lineEdit().setGeometry(12, 2, max(60, w - btn_w - 20), h - 4)


class CustomDateTimeEdit(DateTimeEdit):
    """Enhanced DateTimeEdit with generous width and bug-free text geometry."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.setMinimumWidth(220)
        self.setFixedHeight(36)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        is_btn_visible = hasattr(self, "upButton") and not self.upButton.isHidden()
        btn_w = 68 if is_btn_visible else 0
        self.lineEdit().setGeometry(12, 2, max(80, w - btn_w - 20), h - 4)
