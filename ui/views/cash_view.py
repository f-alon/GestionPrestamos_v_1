from datetime import datetime, date
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog
)
from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, CaptionLabel, CardWidget, ComboBox,
    SingleDirectionScrollArea, qconfig
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
    - SingleDirectionScrollArea to prevent any widget crowding or clipping.
    """
    balance_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_all()

        qconfig.themeChanged.connect(self._on_theme_changed)

    def _init_ui(self):
        # Root layout with zero margins to host scroll area
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Smooth vertical scroll area
        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Vertical)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Container widget for scroll area
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.container)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(18)

        # 1. Header Section
        header_layout = QHBoxLayout()
        header_info = QVBoxLayout()
        self.header_title = TitleLabel("Balances y Arqueos de Caja", self.container)
        self.header_subtitle = CaptionLabel("Supervisión de liquidez disponible, capital colocado en la calle y cierres contables periódicos.", self.container)
        self.header_subtitle.setStyleSheet("font-size: 13px;")
        header_info.addWidget(self.header_title)
        header_info.addWidget(self.header_subtitle)
        header_layout.addLayout(header_info)
        header_layout.addStretch()

        self.btn_refresh = PushButton(FluentIcon.SYNC, "Actualizar", self.container)
        self.btn_refresh.clicked.connect(self.refresh_all)
        header_layout.addWidget(self.btn_refresh)
        content_layout.addLayout(header_layout)

        # 2. Config Card: Capital Inicial (Fondo de Caja)
        card_config = CardWidget(self.container)
        cfg_layout = QVBoxLayout(card_config)
        cfg_layout.setContentsMargins(20, 16, 20, 16)
        cfg_layout.setSpacing(10)

        cfg_header = QVBoxLayout()
        lbl_cfg_title = SubtitleLabel("Fondo de Caja (Capital Inicial)", card_config)
        lbl_cfg_sub = CaptionLabel("Defina el fondo de capital asignado a la caja para otorgar préstamos. Se actualiza en la base de datos.", card_config)
        cfg_header.addWidget(lbl_cfg_title)
        cfg_header.addWidget(lbl_cfg_sub)
        cfg_layout.addLayout(cfg_header)

        cfg_inputs_row = QHBoxLayout()
        cfg_inputs_row.setSpacing(12)

        self.spin_capital_ini = CurrencySpinBox(card_config)
        self.spin_capital_ini.setMinimumWidth(260)
        self.spin_capital_ini.setFixedHeight(36)
        self.spin_capital_ini.setToolTip("Monto de capital inicial disponible para prestar")
        cfg_inputs_row.addWidget(self.spin_capital_ini)

        self.btn_save_cap = PrimaryPushButton(FluentIcon.SAVE, "Guardar Fondo", card_config)
        self.btn_save_cap.setFixedHeight(36)
        self.btn_save_cap.setToolTip("Guardar nuevo capital inicial en la configuración del sistema")
        self.btn_save_cap.clicked.connect(self._save_capital_inicial)
        cfg_inputs_row.addWidget(self.btn_save_cap)
        cfg_inputs_row.addStretch()

        cfg_layout.addLayout(cfg_inputs_row)
        content_layout.addWidget(card_config)

        # 3. Real-time KPI Cards Row
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)

        self.kpi_disponible = KPICard("Capital Disponible en Caja", "$0.00", FluentIcon.MARKET, subtitle="Fondo - Prestado + Cobrado", metric_key="ganancia", parent=self.container)
        self.kpi_en_calle = KPICard("Capital en la Calle", "$0.00", FluentIcon.CALENDAR, subtitle="Principal pendiente de cobro", metric_key="saldo", parent=self.container)
        self.kpi_ganancia_neta = KPICard("Ganancia Neta Cobrada", "$0.00", FluentIcon.ACCEPT, subtitle="Intereses y moras percibidas", metric_key="capital", parent=self.container)

        self.kpi_disponible.setMinimumHeight(105)
        self.kpi_en_calle.setMinimumHeight(105)
        self.kpi_ganancia_neta.setMinimumHeight(105)

        kpi_row.addWidget(self.kpi_disponible)
        kpi_row.addWidget(self.kpi_en_calle)
        kpi_row.addWidget(self.kpi_ganancia_neta)
        content_layout.addLayout(kpi_row)

        # 4. Visual Comparative Chart Card
        chart_card = CardWidget(self.container)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(20, 16, 20, 16)
        chart_layout.setSpacing(10)

        lbl_chart_title = SubtitleLabel("Comparativa Visual de Liquidez y Recupero", chart_card)
        lbl_chart_sub = CaptionLabel("Relación proporcional entre capital disponible, capital en calle y rentabilidad cobrada.", chart_card)
        chart_layout.addWidget(lbl_chart_title)
        chart_layout.addWidget(lbl_chart_sub)

        self.chart = CashComparisonChart(chart_card)
        self.chart.setFixedHeight(220)
        chart_layout.addWidget(self.chart)
        content_layout.addWidget(chart_card)

        # 5. Actions Card (Cierre Diario y Balance Mensual)
        actions_card = CardWidget(self.container)
        actions_card_layout = QVBoxLayout(actions_card)
        actions_card_layout.setContentsMargins(20, 16, 20, 16)
        actions_card_layout.setSpacing(12)

        lbl_act_title = SubtitleLabel("Operaciones Contables y Reportes", actions_card)
        lbl_act_sub = CaptionLabel("Efectúe cierres diarios o descargue el balance consolidado del mes seleccionado.", actions_card)
        actions_card_layout.addWidget(lbl_act_title)
        actions_card_layout.addWidget(lbl_act_sub)

        act_row = QHBoxLayout()
        act_row.setSpacing(14)

        # Cierre Diario button
        self.btn_cierre_diario = PrimaryPushButton(FluentIcon.ACCEPT, "Cierre de Caja Diario", actions_card)
        self.btn_cierre_diario.setFixedHeight(36)
        self.btn_cierre_diario.setToolTip("Congelar y registrar el balance del día actual en la base de datos")
        self.btn_cierre_diario.clicked.connect(self._hacer_cierre_diario)
        act_row.addWidget(self.btn_cierre_diario)

        act_row.addSpacing(16)

        # Month and Year Selector for Monthly Report
        lbl_rep = QLabel("Reporte Mensual:", actions_card)
        lbl_rep.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {ThemePalette.text_primary()};")
        act_row.addWidget(lbl_rep)

        self.combo_mes = ComboBox(actions_card)
        self.combo_mes.setFixedHeight(36)
        self.combo_mes.setMinimumWidth(130)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        for i, m in enumerate(meses, start=1):
            self.combo_mes.addItem(m, userData=i)
        self.combo_mes.setCurrentIndex(datetime.now().month - 1)
        act_row.addWidget(self.combo_mes)

        self.combo_anio = ComboBox(actions_card)
        self.combo_anio.setFixedHeight(36)
        self.combo_anio.setMinimumWidth(95)
        current_year = datetime.now().year
        for y in range(current_year - 2, current_year + 3):
            self.combo_anio.addItem(str(y), userData=y)
        self.combo_anio.setCurrentText(str(current_year))
        act_row.addWidget(self.combo_anio)

        self.btn_exp_pdf = PushButton(FluentIcon.DOCUMENT, "Exportar PDF", actions_card)
        self.btn_exp_pdf.setFixedHeight(36)
        self.btn_exp_pdf.clicked.connect(self._exportar_mensual_pdf)
        act_row.addWidget(self.btn_exp_pdf)

        self.btn_exp_excel = PushButton(FluentIcon.FOLDER, "Exportar Excel", actions_card)
        self.btn_exp_excel.setFixedHeight(36)
        self.btn_exp_excel.clicked.connect(self._exportar_mensual_excel)
        act_row.addWidget(self.btn_exp_excel)

        act_row.addStretch()
        actions_card_layout.addLayout(act_row)
        content_layout.addWidget(actions_card)

        # 6. Table of Daily Closures (Cierres de Caja)
        closures_header = QVBoxLayout()
        closures_header.setSpacing(4)
        lbl_tbl_title = SubtitleLabel("Historial de Cierres de Caja Guardados", self.container)
        lbl_tbl_sub = CaptionLabel("Registro histórico inmutable de los balances diarios guardados.", self.container)
        closures_header.addWidget(lbl_tbl_title)
        closures_header.addWidget(lbl_tbl_sub)
        content_layout.addLayout(closures_header)

        self.table = QTableWidget(self.container)
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
        self.table.setMinimumHeight(280)

        content_layout.addWidget(self.table)

        # Set container to scroll area
        self.scroll_area.setWidget(self.container)
        root_layout.addWidget(self.scroll_area)

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
            font_regular = QFont()
            font_bold = QFont()
            font_bold.setBold(True)

            color_green = QColor("#4ADE80") if is_dark else QColor("#15803D")
            color_blue = QColor("#38BDF8") if is_dark else QColor("#0369A1")

            for i, c in enumerate(cierres):
                it_fecha = QTableWidgetItem(c.fecha)
                it_ini = QTableWidgetItem(f"{CURRENCY_SYMBOL}{c.saldo_inicial:,.2f}")
                it_entradas = QTableWidgetItem(f"+{CURRENCY_SYMBOL}{c.entradas_cobros:,.2f}")
                it_salidas = QTableWidgetItem(f"-{CURRENCY_SYMBOL}{c.salidas_prestamos:,.2f}")
                it_final = QTableWidgetItem(f"{CURRENCY_SYMBOL}{c.saldo_final:,.2f}")
                it_notas = QTableWidgetItem(c.notas or "-")

                for it in [it_fecha, it_ini, it_notas]:
                    it.setForeground(QBrush(fg_main))
                    it.setFont(font_regular)

                it_entradas.setForeground(QBrush(color_green))
                it_entradas.setFont(font_bold)

                it_salidas.setForeground(QBrush(color_blue))
                it_salidas.setFont(font_bold)

                it_final.setForeground(QBrush(fg_main))
                it_final.setFont(font_bold)

                self.table.setItem(i, 0, it_fecha)
                self.table.setItem(i, 1, it_ini)
                self.table.setItem(i, 2, it_entradas)
                self.table.setItem(i, 3, it_salidas)
                self.table.setItem(i, 4, it_final)
                self.table.setItem(i, 5, it_notas)

    def _save_capital_inicial(self):
        val = self.spin_capital_ini.value()
        if val <= 0:
            InfoBar.warning("Valor Inválido", "El capital inicial debe ser mayor a cero.", parent=self)
            return

        set_capital_inicial(val)
        InfoBar.success("Capital Guardado", f"El fondo inicial de caja se actualizó a {CURRENCY_SYMBOL}{val:,.2f}.", parent=self)
        self.refresh_all()
        self.balance_updated.emit()

    def _hacer_cierre_diario(self):
        ok, msg = registrar_cierre_diario()
        if ok:
            InfoBar.success("Cierre Registrado", msg, parent=self, duration=4000)
            self.refresh_all()
            self.balance_updated.emit()
        else:
            InfoBar.warning("Atención", msg, parent=self, duration=5000)

    def _exportar_mensual_pdf(self):
        mes = self.combo_mes.currentData()
        anio = self.combo_anio.currentData()

        default_name = f"Balance_{anio}_{mes:02d}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Balance Mensual en PDF",
            default_name,
            "Archivos PDF (*.pdf)"
        )
        if not file_path:
            return

        ok, msg = exportar_balance_mensual_pdf(anio, mes, file_path)
        if ok:
            InfoBar.success("PDF Generado", f"Reporte guardado con éxito en:\n{file_path}", parent=self, duration=5000)
        else:
            InfoBar.error("Error al Exportar", msg, parent=self, duration=6000)

    def _exportar_mensual_excel(self):
        mes = self.combo_mes.currentData()
        anio = self.combo_anio.currentData()

        default_name = f"Balance_{anio}_{mes:02d}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Balance Mensual en Excel",
            default_name,
            "Archivos Excel (*.xlsx)"
        )
        if not file_path:
            return

        ok, msg = exportar_balance_mensual_excel(anio, mes, file_path)
        if ok:
            InfoBar.success("Excel Generado", f"Balance exportado con éxito en:\n{file_path}", parent=self, duration=5000)
        else:
            InfoBar.error("Error al Exportar", msg, parent=self, duration=6000)
