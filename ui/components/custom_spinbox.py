from PySide6.QtCore import Qt
from qfluentwidgets import DoubleSpinBox, SpinBox, DateEdit, DateTimeEdit


class CurrencySpinBox(DoubleSpinBox):
    """
    Enhanced DoubleSpinBox for currency input.
    Fixes the Qt6/QFluentWidgets lineEdit squishing bug where large amounts
    (e.g., $ 7,000,000.00) were cut off or not displayed properly.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.01, 1_000_000_000.0)
        self.setDecimals(2)
        self.setPrefix("$ ")
        self.setMinimumWidth(240)
        self.setFixedHeight(34)

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
        btn_w = 64 if hasattr(self, "upButton") and self.upButton.isVisible() else 8
        self.lineEdit().setGeometry(10, 2, max(60, w - btn_w - 12), h - 4)


class PercentSpinBox(DoubleSpinBox):
    """Enhanced DoubleSpinBox for percentage rates."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.0, 500.0)
        self.setDecimals(2)
        self.setSuffix(" %")
        self.setMinimumWidth(160)
        self.setFixedHeight(34)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        btn_w = 64 if hasattr(self, "upButton") and self.upButton.isVisible() else 8
        self.lineEdit().setGeometry(10, 2, max(50, w - btn_w - 12), h - 4)


class IntegerSpinBox(SpinBox):
    """Enhanced SpinBox for term durations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(1, 1000)
        self.setMinimumWidth(130)
        self.setFixedHeight(34)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        btn_w = 64 if hasattr(self, "upButton") and self.upButton.isVisible() else 8
        self.lineEdit().setGeometry(10, 2, max(40, w - btn_w - 12), h - 4)


class CustomDateEdit(DateEdit):
    """
    Enhanced DateEdit that fixes Qt6 layout bug where date text was squished
    to 1 pixel and cut off.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy")
        self.setMinimumWidth(180)
        self.setFixedHeight(34)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        btn_w = 64 if hasattr(self, "upButton") and self.upButton.isVisible() else 8
        self.lineEdit().setGeometry(10, 2, max(50, w - btn_w - 12), h - 4)


class CustomDateTimeEdit(DateTimeEdit):
    """
    Enhanced DateTimeEdit that fixes Qt6 layout bug where datetime text was cut off.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.setMinimumWidth(210)
        self.setFixedHeight(34)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        btn_w = 64 if hasattr(self, "upButton") and self.upButton.isVisible() else 8
        self.lineEdit().setGeometry(10, 2, max(60, w - btn_w - 12), h - 4)
