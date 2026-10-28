import os
import subprocess
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QFrame
)
from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, FluentIcon, InfoBar, InfoBarPosition,
    SwitchButton, setTheme, Theme, isDarkTheme, TitleLabel, SubtitleLabel, CaptionLabel,
    BodyLabel, StrongBodyLabel, qconfig
)
from config import DB_PATH, DATA_DIR, APP_NAME, APP_VERSION
from database import get_session, Prestamo
from services.export_service import backup_database, export_prestamos_excel, export_prestamos_csv


class SettingsView(QWidget):
    """
    Settings, Backups, and Data Export View with theme-aware styling.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # Header with Fluent Typography
        header_title = TitleLabel("Configuración y Copias de Seguridad", self)
        header_subtitle = CaptionLabel("Gestión de base de datos SQLite, exportación de reportes y preferencias del sistema.", self)
        header_subtitle.setStyleSheet("font-size: 13px;")
        main_layout.addWidget(header_title)
        main_layout.addWidget(header_subtitle)

        # 1. Export Data Card
        card_export = CardWidget(self)
        ce_layout = QVBoxLayout(card_export)
        ce_layout.setContentsMargins(20, 18, 20, 18)
        ce_layout.setSpacing(12)

        lbl_exp_title = SubtitleLabel("Exportación Contable y Reportes", card_export)
        lbl_exp_desc = CaptionLabel("Generar reportes consolidados de préstamos, estados financieros y pagos amortizados.", card_export)
        ce_layout.addWidget(lbl_exp_title)
        ce_layout.addWidget(lbl_exp_desc)

        exp_btns = QHBoxLayout()
        self.btn_export_excel = PrimaryPushButton(FluentIcon.DOCUMENT, "Exportar a Excel (.xlsx)", card_export)
        self.btn_export_excel.clicked.connect(self._export_excel)
        exp_btns.addWidget(self.btn_export_excel)

        self.btn_export_csv = PushButton(FluentIcon.FOLDER, "Exportar a CSV (.csv)", card_export)
        self.btn_export_csv.clicked.connect(self._export_csv)
        exp_btns.addWidget(self.btn_export_csv)
        exp_btns.addStretch()

        ce_layout.addLayout(exp_btns)
        main_layout.addWidget(card_export)

        # 2. Database & Backups Card
        card_db = CardWidget(self)
        cdb_layout = QVBoxLayout(card_db)
        cdb_layout.setContentsMargins(20, 18, 20, 18)
        cdb_layout.setSpacing(12)

        lbl_db_title = SubtitleLabel("Base de Datos SQLite y Respaldos", card_db)
        cdb_layout.addWidget(lbl_db_title)

        db_size = f"{os.path.getsize(DB_PATH) / 1024:.1f} KB" if os.path.exists(DB_PATH) else "0 KB"
        lbl_db_path = BodyLabel(f"Ubicación del archivo: {DB_PATH}\nTamaño actual: {db_size}", card_db)
        cdb_layout.addWidget(lbl_db_path)

        db_btns = QHBoxLayout()
        self.btn_backup = PushButton(FluentIcon.SAVE, "Hacer Backup Rápido (.db)", card_db)
        self.btn_backup.clicked.connect(self._create_quick_backup)
        db_btns.addWidget(self.btn_backup)

        self.btn_open_folder = PushButton(FluentIcon.FOLDER, "Abrir Directorio de Datos", card_db)
        self.btn_open_folder.clicked.connect(self._open_data_folder)
        db_btns.addWidget(self.btn_open_folder)
        db_btns.addStretch()

        cdb_layout.addLayout(db_btns)
        main_layout.addWidget(card_db)

        # 3. System Preferences Card (Theme toggle)
        card_pref = CardWidget(self)
        cp_layout = QVBoxLayout(card_pref)
        cp_layout.setContentsMargins(20, 18, 20, 18)
        cp_layout.setSpacing(12)

        lbl_pref_title = SubtitleLabel("Apariencia y Preferencias", card_pref)
        cp_layout.addWidget(lbl_pref_title)

        theme_layout = QHBoxLayout()
        lbl_theme = BodyLabel("Modo Oscuro (Dark Theme):", card_pref)
        self.theme_switch = SwitchButton(card_pref)
        self.theme_switch.setChecked(isDarkTheme())
        self.theme_switch.checkedChanged.connect(self._on_theme_toggled)

        theme_layout.addWidget(lbl_theme)
        theme_layout.addWidget(self.theme_switch)
        theme_layout.addStretch()
        cp_layout.addLayout(theme_layout)

        main_layout.addWidget(card_pref)
        main_layout.addStretch()

        # Footer Info
        lbl_footer = CaptionLabel(f"{APP_NAME} v{APP_VERSION} - Motor Financiero PySide6 & Fluent UI", self)
        main_layout.addWidget(lbl_footer)

    def _export_excel(self):
        default_name = f"Reporte_Prestamos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Reporte a Excel", default_name, "Archivos Excel (*.xlsx)")
        if not file_path:
            return

        with get_session() as session:
            prestamos = session.query(Prestamo).order_by(Prestamo.id.desc()).all()
            ok, msg = export_prestamos_excel(prestamos, file_path)

        if ok:
            InfoBar.success("Exportación Exitosa", f"Archivo generado:\n{msg}", parent=self)
        else:
            InfoBar.error("Error al Exportar", msg, parent=self)

    def _export_csv(self):
        default_name = f"Prestamos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Préstamos a CSV", default_name, "Archivos CSV (*.csv)")
        if not file_path:
            return

        with get_session() as session:
            prestamos = session.query(Prestamo).order_by(Prestamo.id.desc()).all()
            ok, msg = export_prestamos_csv(prestamos, file_path)

        if ok:
            InfoBar.success("Exportación Exitosa", f"Archivo CSV generado:\n{msg}", parent=self)
        else:
            InfoBar.error("Error al Exportar", msg, parent=self)

    def _create_quick_backup(self):
        ok, res = backup_database()
        if ok:
            InfoBar.success("Copia de Seguridad Realizada", f"Backup guardado con éxito en:\n{res}", parent=self)
        else:
            InfoBar.error("Fallo al Respaldar", res, parent=self)

    def _open_data_folder(self):
        if os.path.exists(DATA_DIR):
            os.startfile(DATA_DIR)
        else:
            InfoBar.warning("Carpeta no encontrada", "El directorio aún no existe.", parent=self)

    def _on_theme_toggled(self, checked: bool):
        setTheme(Theme.DARK if checked else Theme.LIGHT)
