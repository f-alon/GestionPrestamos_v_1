from datetime import date
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu
)
from qfluentwidgets import (
    SearchLineEdit, SegmentedWidget, PrimaryPushButton, PushButton, FluentIcon,
    InfoBar, InfoBarPosition, TitleLabel, CaptionLabel, MessageBox, qconfig
)
from database import get_session, Prestamo, Cliente
from config import CURRENCY_SYMBOL
from services.financial_service import calcular_prestamo
from services.notification_service import abrir_whatsapp, redactar_mensaje_cobro
from ui.components.kpi_card import KPICard
from ui.dialogs.loan_detail_dialog import LoanDetailDialog
from ui.dialogs.loan_edit_dialog import LoanEditDialog
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
    loan_changed = Signal()

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

        self.btn_edit_loan = PushButton(FluentIcon.EDIT, "Editar Préstamo", self)
        self.btn_edit_loan.setToolTip("Modificar montos o plazos del préstamo seleccionado")
        self.btn_edit_loan.clicked.connect(self._edit_selected_loan)
        filter_layout.addWidget(self.btn_edit_loan)

        self.btn_delete_loan = PushButton(FluentIcon.DELETE, "Eliminar", self)
        self.btn_delete_loan.setStyleSheet("color: #DC2626;")
        self.btn_delete_loan.setToolTip("Eliminar el préstamo seleccionado con confirmación")
        self.btn_delete_loan.clicked.connect(self._delete_selected_loan)
        filter_layout.addWidget(self.btn_delete_loan)

        self.btn_refresh = PushButton(FluentIcon.SYNC, "Actualizar", self)
        self.btn_refresh.clicked.connect(self.refresh_dashboard)
        filter_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(filter_layout)

        # 4. Table with High Contrast, Borders, and Sorting
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

        is_dark = ThemePalette.is_dark()
        fg_main = QColor("#F8FAFC") if is_dark else QColor("#0F172A")
        font_regular = QFont()
        font_bold = QFont()
        font_bold.setBold(True)

        for row_idx, item in enumerate(rows_data):
            p_id = item["id"]
            calc = item["calc"]
            estado = item["estado"]

            # Row background style
            if estado == "TERMINADO":
                bg_color = QColor("#1E2026") if is_dark else QColor("#F8FAFC")
                status_key = "TERMINADO"
                status_text = "TERMINADO"
            elif calc.dias_atraso > 0:
                bg_color = QColor("#3B1015") if is_dark else QColor("#FFF1F2")
                status_key = "MORA"
                status_text = "EN MORA"
            else:
                # Even / Odd rows for clean alternating contrast
                if row_idx % 2 == 0:
                    bg_color = QColor("#18181B") if is_dark else QColor("#FFFFFF")
                else:
                    bg_color = QColor("#1F2228") if is_dark else QColor("#F8FAFC")
                status_key = "AL_DIA"
                status_text = "AL DÍA"

            # Items with numerical sorting
            it_id = NumericTableWidgetItem(f"#{p_id}", float(p_id))
            it_cliente = QTableWidgetItem(item["cliente_nombre"])
            it_venc = QTableWidgetItem(item["vencimiento"])
            it_monto = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.monto_prestado:,.2f}", calc.monto_prestado)
            it_pagado = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.total_abonado:,.2f}", calc.total_abonado)

            # Restante with bold high-contrast color
            it_restante = NumericTableWidgetItem(f"{CURRENCY_SYMBOL}{calc.saldo_restante:,.2f}", calc.saldo_restante)
            if calc.dias_atraso > 0 and estado == "EN_CURSO":
                it_restante.setForeground(QBrush(QColor("#FB7185") if is_dark else QColor("#B91C1C")))
                it_restante.setFont(font_bold)
            elif estado == "TERMINADO":
                it_restante.setForeground(QBrush(QColor("#86EFAC") if is_dark else QColor("#15803D")))
                it_restante.setFont(font_bold)
            else:
                it_restante.setForeground(QBrush(fg_main))
                it_restante.setFont(font_bold)

            # Mora
            it_mora = NumericTableWidgetItem(f"{calc.dias_atraso} días" if calc.dias_atraso > 0 else "-", float(calc.dias_atraso))
            if calc.dias_atraso > 0 and estado == "EN_CURSO":
                it_mora.setForeground(QBrush(QColor("#FB7185") if is_dark else QColor("#B91C1C")))
                it_mora.setFont(font_bold)
            else:
                it_mora.setForeground(QBrush(QColor("#94A3B8") if is_dark else QColor("#64748B")))

            # Set text & backgrounds for data columns
            base_items = [it_id, it_cliente, it_venc, it_monto, it_pagado]
            for it in base_items:
                it.setForeground(QBrush(fg_main))
                it.setFont(font_regular)

            all_items = [it_id, it_cliente, it_venc, it_monto, it_pagado, it_restante, it_mora]
            for col_idx, widget_item in enumerate(all_items):
                widget_item.setBackground(QBrush(bg_color))
                widget_item.setData(Qt.UserRole, p_id)
                self.table.setItem(row_idx, col_idx, widget_item)

            # Estado column: Distinct High-Contrast Pill Badge
            pill_style = ThemePalette.get_status_pill(status_key)
            status_container = QWidget(self.table)
            status_layout = QHBoxLayout(status_container)
            status_layout.setContentsMargins(6, 4, 6, 4)
            status_layout.setAlignment(Qt.AlignCenter)

            status_pill = QLabel(status_text, status_container)
            status_pill.setAlignment(Qt.AlignCenter)
            status_pill.setStyleSheet(f"""
                QLabel {{
                    background-color: {pill_style['bg']};
                    color: {pill_style['text']};
                    border: 1px solid {pill_style['border']};
                    border-radius: 9px;
                    padding: 3px 12px;
                    font-size: 11px;
                    font-weight: 800;
                }}
            """)
            status_layout.addWidget(status_pill)
            self.table.setCellWidget(row_idx, 7, status_container)

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
        dlg.data_changed.connect(self._on_detail_changed)
        dlg.exec()

    def _on_detail_changed(self):
        self.refresh_dashboard()
        self.loan_changed.emit()

    def _edit_selected_loan(self):
        prestamo_id = self._get_selected_prestamo_id()
        if not prestamo_id:
            InfoBar.warning(
                "Seleccionar Préstamo",
                "Por favor seleccione el préstamo que desea editar en la tabla.",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        self._open_loan_edit(prestamo_id)

    def _open_loan_edit(self, prestamo_id: int):
        dlg = LoanEditDialog(prestamo_id, parent=self)
        dlg.loan_edited.connect(self._on_loan_edited)
        dlg.exec()

    def _on_loan_edited(self, prestamo_id: int):
        InfoBar.success("Préstamo Actualizado", f"El préstamo #{prestamo_id} fue modificado con éxito.", parent=self)
        self.refresh_dashboard()
        self.loan_changed.emit()

    def _delete_selected_loan(self):
        prestamo_id = self._get_selected_prestamo_id()
        if not prestamo_id:
            InfoBar.warning(
                "Seleccionar Préstamo",
                "Por favor seleccione el préstamo que desea eliminar de la tabla.",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        self._delete_loan(prestamo_id)

    def _delete_loan(self, prestamo_id: int):
        """
        Deletes a loan with mandatory confirmation modal ("¿Está seguro? Esta acción no se puede deshacer").
        Cascades deletion to all its associated payments and updates balances.
        """
        msg_box = MessageBox(
            "Confirmar Eliminación de Préstamo",
            f"¿Está seguro de eliminar el préstamo #{prestamo_id}?\n\n"
            "⚠️ Esta acción no se puede deshacer y eliminará en cascada todos sus pagos asociados.",
            self.window()
        )
        msg_box.yesButton.setText("Sí")
        msg_box.cancelButton.setText("No")

        if msg_box.exec():
            with get_session() as session:
                p = session.get(Prestamo, prestamo_id)
                if p:
                    session.delete(p)
                    session.commit()

            InfoBar.success(
                "Préstamo Eliminado",
                f"El préstamo #{prestamo_id} y todos sus pagos fueron eliminados del sistema.",
                parent=self,
                duration=4000
            )
            self.refresh_dashboard()
            self.loan_changed.emit()

    def _show_context_menu(self, pos):
        prestamo_id = self._get_selected_prestamo_id()
        if not prestamo_id:
            return

        menu = QMenu(self)
        act_detail = menu.addAction("Ver Detalle y Liquidación")
        act_pago = menu.addAction("Registrar Pago")
        act_edit = menu.addAction("Editar Préstamo")
        act_delete = menu.addAction("Eliminar Préstamo")
        act_whatsapp = menu.addAction("Enviar WhatsApp")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_detail:
            self._open_loan_detail(prestamo_id)
        elif action == act_pago:
            dlg = PaymentDialog(prestamo_id, parent=self)
            if dlg.exec():
                self.refresh_dashboard()
                self.loan_changed.emit()
        elif action == act_edit:
            self._open_loan_edit(prestamo_id)
        elif action == act_delete:
            self._delete_loan(prestamo_id)
        elif action == act_whatsapp:
            with get_session() as session:
                p = session.get(Prestamo, prestamo_id)
                if p and p.cliente and p.cliente.telefono:
                    msg = redactar_mensaje_cobro(p.cliente, p)
                    abrir_whatsapp(p.cliente.telefono, msg)
                else:
                    InfoBar.warning("Sin Teléfono", "No hay teléfono válido para este cliente.", parent=self)
