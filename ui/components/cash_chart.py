from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QBrush, QPen
from PySide6.QtWidgets import QWidget
from ui.theme import ThemePalette
from config import CURRENCY_SYMBOL


class CashComparisonChart(QWidget):
    """
    Modern high-contrast comparative financial bar chart.
    Visualizes:
    - Capital Inicial (Fondo)
    - Capital Disponible en Caja
    - Capital Colocado en Calle
    - Total Cobrado
    - Ganancia Neta Cobrada
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(240)
        self._data = []

    def set_data(self, metrics: list):
        """
        metrics: list of dicts:
        [{'name': str, 'value': float, 'color': str}, ...]
        """
        self._data = metrics
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        is_dark = ThemePalette.is_dark()

        # Background card
        bg_card = QColor(ThemePalette.card_bg())
        border_card = QColor(ThemePalette.card_border())

        painter.setPen(QPen(border_card, 1))
        painter.setBrush(QBrush(bg_card))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 10, 10)

        if not self._data:
            return

        # Find maximum value for scaling
        max_val = max([item["value"] for item in self._data] + [1.0])

        # Margins
        margin_left = 24
        margin_right = 24
        margin_top = 20
        margin_bottom = 20

        usable_w = w - margin_left - margin_right
        usable_h = h - margin_top - margin_bottom

        row_count = len(self._data)
        bar_height = max(18, min(26, int((usable_h - (row_count - 1) * 14) / row_count)))
        spacing = (usable_h - (row_count * bar_height)) / max(1, row_count - 1)

        font_label = QFont("Segoe UI", 9)
        font_label.setBold(True)
        font_value = QFont("Segoe UI", 9)
        font_value.setBold(True)

        y = margin_top

        for item in self._data:
            name = item["name"]
            val = item["value"]
            color_hex = item["color"]

            # Draw labels
            painter.setFont(font_label)
            painter.setPen(QColor(ThemePalette.text_primary()))
            painter.drawText(QRectF(margin_left, y, 220, bar_height), Qt.AlignLeft | Qt.AlignVCenter, name)

            # Bar track (background)
            bar_x = margin_left + 230
            bar_max_w = max(50, usable_w - 230 - 140)

            track_color = QColor("#334155" if is_dark else "#E2E8F0")
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(track_color))
            painter.drawRoundedRect(QRectF(bar_x, y + 4, bar_max_w, bar_height - 8), 4, 4)

            # Bar fill
            pct = max(0.0, min(1.0, val / max_val))
            fill_w = max(6.0, bar_max_w * pct)

            painter.setBrush(QBrush(QColor(color_hex)))
            painter.drawRoundedRect(QRectF(bar_x, y + 4, fill_w, bar_height - 8), 4, 4)

            # Value label on the right
            val_text = f"{CURRENCY_SYMBOL}{val:,.2f}"
            painter.setFont(font_value)
            painter.setPen(QColor(color_hex))
            painter.drawText(QRectF(bar_x + bar_max_w + 14, y, 130, bar_height), Qt.AlignRight | Qt.AlignVCenter, val_text)

            y += bar_height + spacing

