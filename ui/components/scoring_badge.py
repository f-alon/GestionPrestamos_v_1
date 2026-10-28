from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget
from qfluentwidgets import qconfig
from services.scoring_service import ScoringResult
from ui.theme import ThemePalette


class ScoringBadge(QWidget):
    """
    Visual Pill/Badge displaying client credit scoring with adaptive high-contrast styling:
    - ROJO: Alerta Moroso / Riesgo Alto
    - VERDE: Cliente Cumplidor (Sin atrasos)
    - NEUTRO: Sin Historial
    - AZUL: En curso sin atrasos
    """
    def __init__(self, scoring: ScoringResult = None, parent=None):
        super().__init__(parent)
        self._current_scoring = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Hook into theme change to dynamically update contrast
        qconfig.themeChanged.connect(self._on_theme_changed)

        if scoring:
            self.set_scoring(scoring)

    def set_scoring(self, scoring: ScoringResult):
        self._current_scoring = scoring
        self.label.setText(scoring.titulo)
        self.setToolTip(scoring.mensaje)
        self._apply_style()

    def _apply_style(self):
        if not self._current_scoring:
            return

        level = self._current_scoring.nivel
        # Map nivel if needed
        colors = ThemePalette.get_scoring_colors(level)

        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {colors['bg']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 9px;
                padding: 3px 12px;
                font-size: 11px;
                font-weight: 800;
            }}
        """)

    def _on_theme_changed(self):
        self._apply_style()
