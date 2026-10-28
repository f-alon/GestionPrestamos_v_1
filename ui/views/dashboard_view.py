from datetime import date
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu
)
from qfluentwidgets import (
    SearchLineEdit, SegmentedWidget, PrimaryPushButton, PushButton, FluentIcon,
    InfoBar, InfoBarPosition, TitleLabel, CaptionLabel, qconfig
)
from database import get_session, Prestamo, Cliente
from config import CURRENCY_SYMBOL
from services.financial_service import calcular_prestamo
from services.notification_service import abrir_whatsapp, redactar_mensaje_cobro
from ui.components.kpi_card import KPICard
from ui.dialogs.loan_detail_dialog import LoanDetailDialog
from ui.dialogs.payment_dialog import PaymentDialog
from ui.theme import ThemePalette


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts numerically."""
    def __init__(self, text: str, sort_val: float):
        super().__init__(text)
        self.sort_val = sort_val

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_val < other.sort_val
        return super().__lt__(other)


class DashboardView(QWidget):
    """
    Main Dashboard view featuring:
    - 4 KPI summary cards (Capital Prestado, Saldo a Cobrar, Ganancia Estimada, Morosos Activos)
    - Search bar in real-time
    - Filter chips [Todos] [Al día] [Con mora] [Terminados]
    - Quick Action "Nuevo Préstamo" (Ctrl + N)
    - High-contrast color-coded table with sorting, context menu, and double-click to inspect
    """
    request_new_loan = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_filter = "TODOS"
        self._loans_cache = []

        self._init_ui()
        self._setup_shortcuts()
        self.refresh_dashboard()

        # Connect theme change signal
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # 1. Header Section: Fluent Title & Subtitle + "Nuevo Préstamo" button
        header_layout = QHBoxLayout()
        header_info = QVBoxLayout()
        self.header_title = TitleLabel("Panel de Control y Cartera", self)
        self.header_subtitle = CaptionLabel("Monitoreo en tiempo real de colocación, recupero y mora.", self)
        self.header_subtitle.setStyleSheet("font-size: 13px;")
        header_info.addWidget(self.header_title)
        header_info.addWidget(self.header_subtitle)
        header_layout.addLayout(header_info)
        header_layout.addStretch()

        self.btn_new_loan = PrimaryPushButton(FluentIcon.ADD, "Nuevo Préstamo", self)
        self.btn_new_loan.setToolTip("Crear un nuevo préstamo (Ctrl + N)")
        self.btn_new_loan.clicked.connect(self.request_new_loan.emit)
        header_layout.addWidget(self.btn_new_loan)

        main_layout.addLayout(header_layout)

        # 2. KPI Cards Row
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.kpi_capital = KPICard("Capital Prestado", "$0.00", FluentIcon.MARKET, subtitle="Total colocado activo", metric_key="capital", parent=self)
        self.kpi_saldo = KPICard("Saldo a Cobrar", "$0.00", FluentIcon.CALENDAR, subtitle="Capital + Interés + Mora", metric_key="saldo", parent=self)
        self.kpi_ganancia = KPICard("Ganancia Estimada", "$0.00", FluentIcon.ACCEPT, subtitle="Intereses + Punitorios", metric_key="ganancia", parent=self)
        self.kpi_mora = KPICard("Morosos Activos", "0", FluentIcon.INFO, subtitle="Préstamos con atraso", metric_key="mora", parent=self)

        kpi_layout.addWidget(self.kpi_capital)
        kpi_layout.addWidget(self.kpi_saldo)
        kpi_layout.addWidget(self.kpi_ganancia)
        kpi_layout.addWidget(self.kpi_mora)
        main_layout.addLayout(kpi_layout)

        # 3. Filter Bar: Search + Chip Filters (Todos, Al día, Con mora, Terminados)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Buscar por cliente, teléfono o ID de préstamo...")
        self.search_box.setFixedWidth(320)
        self.search_box.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_box)

        self.filter_chips = SegmentedWidget(self)
        self.filter_chips.addItem("TODOS", "Todos")
        self.filter_chips.addItem("AL_DIA", "Al día")
        self.filter_chips.addItem("CON_MORA", "Con mora")
        self.filter_chips.addItem("TERMINADOS", "Terminados")
        self.filter_chips.setCurrentItem("TODOS")
        self.filter_chips.currentItemChanged.connect(self._on_chip_changed)
        filter_layout.addWidget(self.filter_chips)

        filter_layout.addStretch()

        self.btn_refresh = PushButton(FluentIcon.SYNC, "Actualizar", self)
        self.btn_refresh.clicked.connect(self.refresh_dashboard)
        filter_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(filter_layout)

        # 4. Table with High Contrast and Sorting
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Cliente", "Vencimiento", "Monto", "Pagado", "Restante", "Mora (días)", "Estado"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        main_layout.addWidget(self.table)

    def _setup_shortcuts(self):
        shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_new.activated.connect(self.request_new_loan.emit)

    def _on_chip_changed(self, item_id: str):
        self._current_filter = item_id
        self._apply_filters()

    def _on_theme_changed(self):
        self._apply_filters()

    def refresh_dashboard(self):
        """Reloads all loans and updates KPIs and Table."""
        with get_session() as session:
            prestamos = session.query(Prestamo).order_by(Prestamo.id.desc()).all()

            self._loans_cache = []
            total_prestado_activo = 0.0
            total_saldo_cobrar = 0.0
            total_ganancia_estimada = 0.0
            morosos_activos = 0

            for p in prestamos:
                calc = calcular_prestamo(p)
                cliente_nombre = p.cliente.nombre_completo if p.cliente else "Desconocido"
                cliente_tel = p.cliente.telefono if p.cliente else ""

                if p.estado == "EN_CURSO":
                    total_prestado_activo += calc.monto_prestado
                    total_saldo_cobrar += calc.saldo_restante
                    total_ganancia_estimada += (calc.interes_monto + calc.mora_acumulada)
                    if calc.dias_atraso > 0:
                        morosos_activos += 1

                self._loans_cache.append({
                    "id": p.id,
                    "prestamo": p,
                    "calc": calc,
                    "cliente_nombre": cliente_nombre,
                    "cliente_tel": cliente_tel,
                    "estado": p.estado,
                    "vencimiento": p.fecha_fin,
                    "monto": calc.monto_prestado,
                    "pagado": calc.total_abonado,
                    "restante": calc.saldo_restante,
                    "mora_dias": calc.dias_atraso,
                    "mora_monto": calc.mora_acumulada
                })

            # Update KPIs
            self.kpi_capital.set_value(f"{CURRENCY_SYMBOL}{total_prestado_activo:,.2f}")
            self.kpi_saldo.set_value(f"{CURRENCY_SYMBOL}{total_saldo_cobrar:,.2f}")
            self.kpi_ganancia.set_value(f"{CURRENCY_SYMBOL}{total_ganancia_estimada:,.2f}")
            self.kpi_mora.set_value(str(morosos_activos), f"{morosos_activos} con punitorios vigentes" if morosos_activos > 0 else "Al día")

        self._apply_filters()

    def _apply_filters(self):
        query = self.search_box.text().strip().lower()
        filter_mode = self._current_filter

        filtered = []
        for item in self._loans_cache:
            if filter_mode == "AL_DIA" and (item["estado"] != "EN_CURSO" or item["mora_dias"] > 0):
                continue
            if filter_mode == "CON_MORA" and (item["estado"] != "EN_CURSO" or item["mora_dias"] <= 0):
                continue
            if filter_mode == "TERMINADOS" and item["estado"] != "TERMINADO":
                continue

            if query:
                match = (
                    query in str(item["id"]) or
                    query in item["cliente_nombre"].lower() or
                    query in item["cliente_tel"]
                )
                if not match:
                    continue

            filtered.append(item)

        self._populate_table(filtered)

    def _populate_table(self, rows_data):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows_data))

        font_bold = QFont()
        font_bold.setBold(True)

        for row_idx, item in enumerate(rows_data):
            p_id = item["id"]
            calc = item["calc"]
            estado = item["estado"]

            # Adaptive high-contrast colors from ThemePalette
            if estado == "TERMINADO":
                bg_color, fg_color = ThemePalette.get_table_colors("TERMINADO")
                status_text = "TERMINADO"
            elif calc.dias_atraso > 0:
                bg_color, fg_color = ThemePalette.get_table_colors("MORA")
                status_text = "EN MORA"
            else:
                bg_color, fg_color = ThemePalette.get_table_colors("AL_DIA")
                status_text = "AL DÍA"

            # Items with numerical sorting
            it_id = NumericTableWidgetItem(f"#{p_id}", float(p_id))
            it_cliente = QTableWidgetItem(item["cliente_nombre"])
            it_venc = QTableWidgetItem(item["vencimiento"])
            it_monto = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.monto_prestado:,.2f}", calc.monto_prestado)
            it_pagado = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.total_abonado:,.2f}", calc.total_abonado)
            it_restante = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.saldo_restante:,.2f}", calc.saldo_restante)
            it_mora = NumericTableWidgetItem(f"{calc.dias_atraso} días" if calc.dias_atraso > 0 else "-", float(calc.dias_atraso))
            it_estado = QTableWidgetItem(status_text)

            it_estado.setFont(font_bold)
            it_estado.setForeground(QBrush(fg_color))

            if calc.dias_atraso > 0 and estado == "EN_CURSO":
                it_mora.setFont(font_bold)
                it_mora.setForeground(QBrush(fg_color))
                it_restante.setFont(font_bold)
                it_restante.setForeground(QBrush(fg_color))

            row_items = [it_id, it_cliente, it_venc, it_monto, it_pagado, it_restante, it_mora, it_estado]
            for col_idx, widget_item in enumerate(row_items):
                widget_item.setBackground(QBrush(bg_color))
                widget_item.setData(Qt.UserRole, p_id)
                self.table.setItem(row_idx, col_idx, widget_item)

        self.table.setSortingEnabled(True)

    def _get_selected_prestamo_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _on_row_double_clicked(self, item):
        prestamo_id = item.data(Qt.UserRole)
        if prestamo_id:
            self._open_loan_detail(prestamo_id)

    def _open_loan_detail(self, prestamo_id: int):
        dlg = LoanDetailDialog(prestamo_id, parent=self)
        dlg.data_changed.connect(self.refresh_dashboard)
        dlg.exec()

    def _show_context_menu(self, pos):
        prestamo_id = self._get_selected_prestamo_id()
        if not prestamo_id:
            return

        menu = QMenu(self)
        act_detail = menu.addAction("Ver Detalle y Liquidación")
        act_pago = menu.addAction("Registrar Pago")
        act_whatsapp = menu.addAction("Enviar WhatsApp")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_detail:
            self._open_loan_detail(prestamo_id)
        elif action == act_pago:
            dlg = PaymentDialog(prestamo_id, parent=self)
            if dlg.exec():
                self.refresh_dashboard()
        elif action == act_whatsapp:
            with get_session() as session:
                p = session.get(Prestamo, prestamo_id)
                if p and p.cliente and p.cliente.telefono:
                    msg = redactar_mensaje_cobro(p.cliente, p)
                    abrir_whatsapp(p.cliente.telefono, msg)
                else:
                    InfoBar.warning("Sin Teléfono", "No hay teléfono válido para este cliente.", parent=self)
