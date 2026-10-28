from datetime import datetime, date
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog
)
from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, CaptionLabel, CardWidget, ComboBox, qconfig
)
from database import get_session, CierreCaja
from config import CURRENCY_SYMBOL
from services.cash_service import (
    get_capital_inicial, set_capital_inicial, calcular_balance_caja,
    registrar_cierre_diario, exportar_balance_mensual_pdf, exportar_balance_mensual_excel
)
from ui.components.kpi_card import KPICard
from ui.components.custom_spinbox import CurrencySpinBox
from ui.components.cash_chart import CashComparisonChart
from ui.theme import ThemePalette


class CashView(QWidget):
    """
    View for 'Balances / Arqueos':
    - Configure Initial Capital (Cash Fund)
    - Real-time Cards: Available Liquid Cash, Capital in Street, Net Collected Profit
    - Interactive visual comparative chart
    - Daily Cash Closure (Cierre Diario)
    - Monthly Balance Consolidation with PDF and Excel export
    - Historical Table of Closures
    """
    balance_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_all()

        qconfig.themeChanged.connect(self._on_theme_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        header_info = QVBoxLayout()
        self.header_title = TitleLabel("Balances y Arqueos de Caja", self)
        self.header_subtitle = CaptionLabel("Supervisión de liquidez disponible, capital colocado en la calle y cierres contables periódicos.", self)
        self.header_subtitle.setStyleSheet("font-size: 13px;")
        header_info.addWidget(self.header_title)
        header_info.addWidget(self.header_subtitle)
        header_layout.addLayout(header_info)
        header_layout.addStretch()

        self.btn_refresh = PushButton(FluentIcon.SYNC, "Actualizar", self)
        self.btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)

        # 1. Config Card: Capital Inicial
        card_config = CardWidget(self)
        cfg_layout = QHBoxLayout(card_config)
        cfg_layout.setContentsMargins(18, 12, 18, 12)
        cfg_layout.setSpacing(14)

        lbl_cfg_title = QLabel("Capital Inicial en Caja (Fondo para Prestar):", card_config)
        lbl_cfg_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {ThemePalette.text_primary()};")
        cfg_layout.addWidget(lbl_cfg_title)

        self.spin_capital_ini = CurrencySpinBox(card_config)
        self.spin_capital_ini.setMinimumWidth(220)
        cfg_layout.addWidget(self.spin_capital_ini)

        self.btn_save_cap = PrimaryPushButton(FluentIcon.SAVE, "Guardar Fondo", card_config)
        self.btn_save_cap.clicked.connect(self._save_capital_inicial)
        cfg_layout.addWidget(self.btn_save_cap)
        cfg_layout.addStretch()

        main_layout.addWidget(card_config)

        # 2. Real-time KPI Cards Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self.kpi_disponible = KPICard("Capital Disponible en Caja", "$0.00", FluentIcon.MARKET, subtitle="Fondo - Prestado + Cobrado", metric_key="ganancia", parent=self)
        self.kpi_en_calle = KPICard("Capital en la Calle", "$0.00", FluentIcon.CALENDAR, subtitle="Principal pendiente de cobro", metric_key="saldo", parent=self)
        self.kpi_ganancia_neta = KPICard("Ganancia Neta Cobrada", "$0.00", FluentIcon.ACCEPT, subtitle="Intereses y moras percibidas", metric_key="capital", parent=self)

        kpi_row.addWidget(self.kpi_disponible)
        kpi_row.addWidget(self.kpi_en_calle)
        kpi_row.addWidget(self.kpi_ganancia_neta)
        main_layout.addLayout(kpi_row)

        # 3. Visual Comparative Chart
        self.chart = CashComparisonChart(self)
        main_layout.addWidget(self.chart)

        # 4. Actions & Controls for Cierres and Monthly Report
        actions_card = CardWidget(self)
        act_layout = QHBoxLayout(actions_card)
        act_layout.setContentsMargins(16, 12, 16, 12)
        act_layout.setSpacing(12)

        # Cierre Diario button
        self.btn_cierre_diario = PrimaryPushButton(FluentIcon.ACCEPT, "Cierre de Caja Diario", actions_card)
        self.btn_cierre_diario.setToolTip("Congelar y registrar el balance del día actual en la base de datos")
        self.btn_cierre_diario.clicked.connect(self._hacer_cierre_diario)
        act_layout.addWidget(self.btn_cierre_diario)

        # Separator / spacing
        act_layout.addSpacing(20)

        # Month and Year Selector for Monthly Report
        lbl_rep = QLabel("Balance Mensual:", actions_card)
        lbl_rep.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {ThemePalette.text_primary()};")
        act_layout.addWidget(lbl_rep)

        self.combo_mes = ComboBox(actions_card)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        for i, m in enumerate(meses, start=1):
            self.combo_mes.addItem(m, userData=i)
        self.combo_mes.setCurrentIndex(datetime.now().month - 1)
        act_layout.addWidget(self.combo_mes)

        self.combo_anio = ComboBox(actions_card)
        current_year = datetime.now().year
        for y in range(current_year - 2, current_year + 3):
            self.combo_anio.addItem(str(y), userData=y)
        self.combo_anio.setCurrentText(str(current_year))
        act_layout.addWidget(self.combo_anio)

        self.btn_exp_pdf = PushButton(FluentIcon.DOCUMENT, "Exportar PDF", actions_card)
        self.btn_exp_pdf.clicked.connect(self._exportar_mensual_pdf)
        act_layout.addWidget(self.btn_exp_pdf)

        self.btn_exp_excel = PushButton(FluentIcon.FOLDER, "Exportar Excel", actions_card)
        self.btn_exp_excel.clicked.connect(self._exportar_mensual_excel)
        act_layout.addWidget(self.btn_exp_excel)

        act_layout.addStretch()
        main_layout.addWidget(actions_card)

        # 5. Table of Daily Closures (Cierres de Caja)
        lbl_tbl_title = SubtitleLabel("Historial de Cierres de Caja Guardados", self)
        main_layout.addWidget(lbl_tbl_title)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Fecha Cierre", "Saldo Inicial", "Entradas (Cobros)", "Salidas (Préstamos)", "Saldo Final", "Notas"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        main_layout.addWidget(self.table)

    def _on_theme_changed(self):
        self.chart.update()
        self.refresh_all()

    def refresh_all(self):
        # 1. Update initial capital spin
        cap_ini = get_capital_inicial()
        self.spin_capital_ini.blockSignals(True)
        self.spin_capital_ini.setValue(cap_ini)
        self.spin_capital_ini.blockSignals(False)

        # 2. Compute metrics
        balance = calcular_balance_caja()

        # Update cards
        self.kpi_disponible.set_value(f"{CURRENCY_SYMBOL}{balance.capital_disponible_caja:,.2f}")
        self.kpi_en_calle.set_value(f"{CURRENCY_SYMBOL}{balance.capital_en_calle:,.2f}")
        self.kpi_ganancia_neta.set_value(f"{CURRENCY_SYMBOL}{balance.ganancia_neta_cobrada:,.2f}")

        # 3. Update Chart
        chart_data = [
            {"name": "Fondo Inicial", "value": balance.capital_inicial, "color": "#0284C7"},
            {"name": "Disponible en Caja", "value": max(0.0, balance.capital_disponible_caja), "color": "#16A34A"},
            {"name": "Colocado en la Calle", "value": balance.capital_en_calle, "color": "#EA580C"},
            {"name": "Total Cobrado", "value": balance.total_cobrado, "color": "#10B981"},
            {"name": "Ganancia Neta Cobrada", "value": balance.ganancia_neta_cobrada, "color": "#8B5CF6"}
        ]
        self.chart.set_data(chart_data)

        # 4. Populate Closures Table
        self._populate_closures_table()

    def _populate_closures_table(self):
        with get_session() as session:
            cierres = session.query(CierreCaja).order_by(CierreCaja.fecha.desc()).all()

            self.table.setRowCount(len(cierres))
            is_dark = ThemePalette.is_dark()
            fg_main = QColor("#F8FAFC") if is_dark else QColor("#0F172A")
            color_green = QColor("#86EFAC") if is_dark else QColor("#15803D")
            color_blue = QColor("#93C5FD") if is_dark else QColor("#0369A1")

            font_bold = QFont()
            font_bold.setBold(True)

            for row, c in enumerate(cierres):
                it_fecha = QTableWidgetItem(c.fecha)
                it_ini = QTableWidgetItem(f"{CURRENCY_SYMBOL}{c.saldo_inicial:,.2f}")
                it_in = QTableWidgetItem(f"+{CURRENCY_SYMBOL}{c.entradas_cobros:,.2f}")
                it_out = QTableWidgetItem(f"-{CURRENCY_SYMBOL}{c.salidas_prestamos:,.2f}")
                it_fin = QTableWidgetItem(f"{CURRENCY_SYMBOL}{c.saldo_final:,.2f}")
                it_notas = QTableWidgetItem(c.notas or "-")

                it_fecha.setForeground(QBrush(fg_main))
                it_ini.setForeground(QBrush(fg_main))
                it_in.setForeground(QBrush(color_green))
                it_in.setFont(font_bold)
                it_out.setForeground(QBrush(color_blue))
                it_out.setFont(font_bold)
                it_fin.setForeground(QBrush(fg_main))
                it_fin.setFont(font_bold)
                it_notas.setForeground(QBrush(QColor(ThemePalette.text_secondary())))

                self.table.setItem(row, 0, it_fecha)
                self.table.setItem(row, 1, it_ini)
                self.table.setItem(row, 2, it_in)
                self.table.setItem(row, 3, it_out)
                self.table.setItem(row, 4, it_fin)
                self.table.setItem(row, 5, it_notas)

    def _save_capital_inicial(self):
        val = self.spin_capital_ini.value()
        set_capital_inicial(val)
        InfoBar.success("Fondo Guardado", f"El capital inicial se actualizó a {CURRENCY_SYMBOL}{val:,.2f}.", parent=self)
        self.refresh_all()
        self.balance_updated.emit()

    def _hacer_cierre_diario(self):
        ok, msg = registrar_cierre_diario()
        if ok:
            InfoBar.success("Cierre Registrado", msg, parent=self)
            self.refresh_all()
        else:
            InfoBar.warning("Atención", msg, parent=self)

    def _exportar_mensual_pdf(self):
        mes = self.combo_mes.currentData()
        anio = int(self.combo_anio.currentText())
        default_name = f"Balance_Mensual_{anio}_{mes:02d}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Balance Mensual a PDF", default_name, "Documentos PDF (*.pdf)")
        if not file_path:
            return

        ok, res = exportar_balance_mensual_pdf(anio, mes, file_path)
        if ok:
            InfoBar.success("PDF Generado", f"Reporte guardado con éxito:\n{res}", parent=self)
        else:
            InfoBar.error("Error al exportar", res, parent=self)

    def _exportar_mensual_excel(self):
        mes = self.combo_mes.currentData()
        anio = int(self.combo_anio.currentText())
        default_name = f"Balance_Mensual_{anio}_{mes:02d}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Balance Mensual a Excel", default_name, "Planillas Excel (*.xlsx)")
        if not file_path:
            return

        ok, res = exportar_balance_mensual_excel(anio, mes, file_path)
        if ok:
            InfoBar.success("Excel Generado", f"Reporte guardado con éxito:\n{res}", parent=self)
        else:
            InfoBar.error("Error al exportar", res, parent=self)

