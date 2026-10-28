from PySide6.QtGui import QColor
from qfluentwidgets import isDarkTheme


class ThemePalette:
    """
    Centralized high-contrast color palette manager for Light and Dark themes.
    Strictly calibrated to exceed WCAG AAA standards for maximum readability and visual clarity.
    """

    @classmethod
    def is_dark(cls) -> bool:
        return isDarkTheme()

    @classmethod
    def text_primary(cls) -> str:
        return "#F8FAFC" if cls.is_dark() else "#0F172A"

    @classmethod
    def text_secondary(cls) -> str:
        return "#CBD5E1" if cls.is_dark() else "#334155"

    @classmethod
    def text_muted(cls) -> str:
        return "#94A3B8" if cls.is_dark() else "#475569"

    @classmethod
    def accent_primary(cls) -> str:
        return "#38BDF8" if cls.is_dark() else "#0284C7"

    @classmethod
    def card_bg(cls) -> str:
        return "#1E222A" if cls.is_dark() else "#FFFFFF"

    @classmethod
    def card_border(cls) -> str:
        return "#334155" if cls.is_dark() else "#CBD5E1"

    @classmethod
    def input_border(cls) -> str:
        return "#475569" if cls.is_dark() else "#94A3B8"

    @classmethod
    def highlight_box(cls) -> dict:
        if cls.is_dark():
            return {
                "bg": "#082F49",
                "border": "#38BDF8",
                "title": "#7DD3FC",
                "text": "#F0F9FF"
            }
        else:
            return {
                "bg": "#E0F2FE",
                "border": "#0284C7",
                "title": "#0369A1",
                "text": "#0C4A6E"
            }

    @classmethod
    def get_table_colors(cls, row_type: str) -> tuple[QColor, QColor]:
        """
        Returns (QColor(background), QColor(foreground)) for table rows.
        High contrast guaranteed for both light and dark backgrounds.
        """
        if cls.is_dark():
            if row_type == "AL_DIA":
                # Dark emerald background + crisp light mint text
                return QColor("#0B291A"), QColor("#86EFAC")
            elif row_type == "MORA":
                # Dark burgundy background + crisp bright coral text
                return QColor("#3B1015"), QColor("#FCA5A5")
            elif row_type == "TERMINADO":
                # Dark neutral background + readable light gray text
                return QColor("#1E2026"), QColor("#CBD5E1")
            else:
                return QColor("#18181B"), QColor("#F8FAFC")
        else:
            if row_type == "AL_DIA":
                # Clean soft green tint + pitch dark text for maximum legibility
                return QColor("#DCFCE7"), QColor("#0F172A")
            elif row_type == "MORA":
                # Clean soft rose tint + deep red/black text for maximum legibility
                return QColor("#FEE2E2"), QColor("#0F172A")
            elif row_type == "TERMINADO":
                # Clean soft gray tint + deep slate text
                return QColor("#F1F5F9"), QColor("#334155")
            else:
                return QColor("#FFFFFF"), QColor("#0F172A")

    @classmethod
    def get_status_pill(cls, status: str) -> dict:
        """
        Returns {'bg': str, 'border': str, 'text': str} for table status pill cells.
        """
        if cls.is_dark():
            if status == "MORA":
                return {"bg": "#450A0A", "border": "#EF4444", "text": "#FCA5A5"}
            elif status == "AL_DIA":
                return {"bg": "#052E16", "border": "#22C55E", "text": "#86EFAC"}
            else:
                return {"bg": "#1E293B", "border": "#64748B", "text": "#E2E8F0"}
        else:
            if status == "MORA":
                return {"bg": "#FEE2E2", "border": "#DC2626", "text": "#7F1D1D"}
            elif status == "AL_DIA":
                return {"bg": "#DCFCE7", "border": "#16A34A", "text": "#14532D"}
            else:
                return {"bg": "#F1F5F9", "border": "#64748B", "text": "#1E293B"}

    @classmethod
    def get_scoring_colors(cls, level: str) -> dict:
        """
        Returns {'bg': str, 'border': str, 'text': str} for badges and alert banners.
        """
        if cls.is_dark():
            if level == "ROJO":
                return {
                    "bg": "#450A0A",
                    "border": "#EF4444",
                    "text": "#FCA5A5"
                }
            elif level == "VERDE":
                return {
                    "bg": "#052E16",
                    "border": "#22C55E",
                    "text": "#86EFAC"
                }
            elif level == "AZUL":
                return {
                    "bg": "#0C2A44",
                    "border": "#38BDF8",
                    "text": "#BAE6FD"
                }
            else:  # NEUTRO
                return {
                    "bg": "#27272A",
                    "border": "#71717A",
                    "text": "#F4F4F5"
                }
        else:
            if level == "ROJO":
                return {
                    "bg": "#FEE2E2",
                    "border": "#DC2626",
                    "text": "#7F1D1D"
                }
            elif level == "VERDE":
                return {
                    "bg": "#DCFCE7",
                    "border": "#16A34A",
                    "text": "#14532D"
                }
            elif level == "AZUL":
                return {
                    "bg": "#DBEAFE",
                    "border": "#2563EB",
                    "text": "#1E3A8A"
                }
            else:  # NEUTRO
                return {
                    "bg": "#F1F5F9",
                    "border": "#64748B",
                    "text": "#0F172A"
                }

    @classmethod
    def get_kpi_colors(cls, metric_key: str) -> dict:
        """
        Returns adaptive high-contrast colors for KPI card metrics.
        """
        is_d = cls.is_dark()
        if metric_key == "capital":
            accent = "#38BDF8" if is_d else "#0369A1"
        elif metric_key == "saldo":
            accent = "#FB923C" if is_d else "#C2410C"
        elif metric_key == "ganancia":
            accent = "#4ADE80" if is_d else "#15803D"
        elif metric_key == "mora":
            accent = "#FB7185" if is_d else "#B91C1C"
        else:
            accent = "#60A5FA" if is_d else "#1D4ED8"

        return {
            "accent": accent,
            "title": "#CBD5E1" if is_d else "#1E293B",
            "subtitle": "#94A3B8" if is_d else "#475569"
        }
