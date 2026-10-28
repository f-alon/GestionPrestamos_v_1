from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget
from qfluentwidgets import SimpleCardWidget, IconWidget, FluentIconBase, qconfig
from ui.theme import ThemePalette


class KPICard(SimpleCardWidget):
    """
    Modern Fluent Card for Dashboard KPIs with high-contrast theme styling.
    """
    def __init__(self, title: str, initial_value: str, icon: FluentIconBase, subtitle: str = "", metric_key: str = "capital", parent=None):
        super().__init__(parent)
        self.metric_key = metric_key
        self.raw_title = title
        self.raw_subtitle = subtitle
        self.raw_value = initial_value
        self.setFixedHeight(108)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # Icon container
        self.icon_box = QWidget(self)
        self.icon_box.setFixedSize(50, 50)
        icon_box_layout = QVBoxLayout(self.icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_box_layout.setAlignment(Qt.AlignCenter)

        self.icon_widget = IconWidget(icon, self.icon_box)
        self.icon_widget.setFixedSize(26, 26)
        icon_box_layout.addWidget(self.icon_widget)
        layout.addWidget(self.icon_box)

        # Text information
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.title_label = QLabel(title, self)
        self.value_label = QLabel(initial_value, self)
        self.subtitle_label = QLabel(subtitle, self)

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.value_label)
        info_layout.addWidget(self.subtitle_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        self._apply_theme_styles()
        qconfig.themeChanged.connect(self._apply_theme_styles)

    def _apply_theme_styles(self):
        palette = ThemePalette.get_kpi_colors(self.metric_key)
        accent = palette["accent"]
        title_color = palette["title"]
        sub_color = palette["subtitle"]
        is_dark = ThemePalette.is_dark()

        card_bg = "#1E222A" if is_dark else "#FFFFFF"
        card_border = "#334155" if is_dark else "#CBD5E1"

        self.setStyleSheet(f"""
            KPICard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
        """)

        self.icon_box.setStyleSheet(f"""
            QWidget {{
                background-color: {accent}22;
                border-radius: 12px;
                border: 2px solid {accent};
            }}
        """)

        self.title_label.setStyleSheet(f"color: {title_color}; font-size: 13px; font-weight: 700;")
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 22px; font-weight: 900;")
        self.subtitle_label.setStyleSheet(f"color: {sub_color}; font-size: 11px; font-weight: 500;")
        self.subtitle_label.setVisible(bool(self.raw_subtitle))

    def set_value(self, value: str, subtitle: str = None):
        self.raw_value = value
        self.value_label.setText(value)
        if subtitle is not None:
            self.raw_subtitle = subtitle
            self.subtitle_label.setText(subtitle)
            self.subtitle_label.setVisible(bool(subtitle))
