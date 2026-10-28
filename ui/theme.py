from PySide6.QtGui import QColor
from qfluentwidgets import isDarkTheme


class ThemePalette:
    """
    Centralized high-contrast color palette manager for Light and Dark themes.
    Ensures optimal readability and WCAG AA contrast for text, badges, cards, and tables.
    """

    @classmethod
    def is_dark(cls) -> bool:
        return isDarkTheme()

    @classmethod
    def text_primary(cls) -> str:
        return "#F9FAFB" if cls.is_dark() else "#111827"

    @classmethod
    def text_secondary(cls) -> str:
        return "#9CA3AF" if cls.is_dark() else "#4B5563"

    @classmethod
    def text_muted(cls) -> str:
        return "#6B7280" if cls.is_dark() else "#6B7280"

    @classmethod
    def card_border(cls) -> str:
        return "#374151" if cls.is_dark() else "#E5E7EB"

    @classmethod
    def highlight_box(cls) -> dict:
        if cls.is_dark():
            return {
                "bg": "#0C2A44",
                "border": "#0284C7",
                "title": "#38BDF8",
                "text": "#E0F2FE"
            }
        else:
            return {
                "bg": "#F0F9FF",
                "border": "#BAE6FD",
                "title": "#0369A1",
                "text": "#0284C7"
            }

    @classmethod
    def get_table_colors(cls, row_type: str) -> tuple[QColor, QColor]:
        """
        Returns (QColor(background), QColor(foreground)) for table rows.
        High contrast guaranteed for both light and dark backgrounds.
        """
        if cls.is_dark():
            if row_type == "AL_DIA":
                # Dark forest green background + crisp light emerald text
                return QColor("#092816"), QColor("#4ADE80")
            elif row_type == "MORA":
                # Dark ruby background + crisp light coral text
                return QColor("#381116"), QColor("#FB7185")
            elif row_type == "TERMINADO":
                # Dark neutral background + readable light gray text
                return QColor("#1F2228"), QColor("#9CA3AF")
            else:
                return QColor("#18181B"), QColor("#F4F4F5")
        else:
            if row_type == "AL_DIA":
                # Soft mint green + deep dark green text (> 7:1 contrast)
                return QColor("#DCFCE7"), QColor("#14532D")
            elif row_type == "MORA":
                # Soft red rose + deep dark burgundy text (> 7:1 contrast)
                return QColor("#FEE2E2"), QColor("#7F1D1D")
            elif row_type == "TERMINADO":
                # Soft light gray + slate gray text (> 6:1 contrast)
                return QColor("#F3F4F6"), QColor("#374151")
            else:
                return QColor("#FFFFFF"), QColor("#111827")

    @classmethod
    def get_scoring_colors(cls, level: str) -> dict:
        """
        Returns {'bg': str, 'border': str, 'text': str} for badges and alert banners.
        """
        if cls.is_dark():
            if level == "ROJO":
                return {
                    "bg": "#3B0E12",
                    "border": "#DC2626",
                    "text": "#FCA5A5"
                }
            elif level == "VERDE":
                return {
                    "bg": "#062C18",
                    "border": "#16A34A",
                    "text": "#86EFAC"
                }
            elif level == "AZUL":
                return {
                    "bg": "#0D253F",
                    "border": "#2563EB",
                    "text": "#93C5FD"
                }
            else:  # NEUTRO
                return {
                    "bg": "#27272A",
                    "border": "#52525B",
                    "text": "#E4E4E7"
                }
        else:
            if level == "ROJO":
                return {
                    "bg": "#FEE2E2",
                    "border": "#F87171",
                    "text": "#991B1B"
                }
            elif level == "VERDE":
                return {
                    "bg": "#DCFCE7",
                    "border": "#4ADE80",
                    "text": "#166534"
                }
            elif level == "AZUL":
                return {
                    "bg": "#DBEAFE",
                    "border": "#60A5FA",
                    "text": "#1E40AF"
                }
            else:  # NEUTRO
                return {
                    "bg": "#F3F4F6",
                    "border": "#CBD5E1",
                    "text": "#1E293B"
                }

    @classmethod
    def get_kpi_colors(cls, metric_key: str) -> dict:
        """
        Returns adaptive colors for KPI card metrics.
        """
        is_d = cls.is_dark()
        if metric_key == "capital":
            accent = "#38BDF8" if is_d else "#0284C7"
        elif metric_key == "saldo":
            accent = "#FB923C" if is_d else "#C2410C"
        elif metric_key == "ganancia":
            accent = "#4ADE80" if is_d else "#15803D"
        elif metric_key == "mora":
            accent = "#FB7185" if is_d else "#B91C1C"
        else:
            accent = "#60A5FA" if is_d else "#2563EB"

        return {
            "accent": accent,
            "title": "#9CA3AF" if is_d else "#4B5563",
            "subtitle": "#6B7280" if is_d else "#6B7280"
        }

