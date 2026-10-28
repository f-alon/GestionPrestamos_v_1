from datetime import date
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from qfluentwidgets import (
    PushButton, PrimaryPushButton, InfoBar, InfoBarPosition, CardWidget,
    FluentIcon, TitleLabel, SubtitleLabel, CaptionLabel, StrongBodyLabel,
    BodyLabel, MessageBox, qconfig
)
from database import get_session, Prestamo, Pago
from config import CURRENCY_SYMBOL
from services.financial_service import calcular_prestamo
from services.scoring_service import evaluar_cliente
from services.notification_service import redactar_mensaje_cobro, abrir_whatsapp
from ui.dialogs.payment_dialog import PaymentDialog
from ui.dialogs.loan_edit_dialog import LoanEditDialog
from ui.components.scoring_badge import ScoringBadge
from ui.theme import ThemePalette


class LoanDetailDialog(QDialog):
    """Detailed view for a loan, financial breakdown, payments, and actions."""
    data_changed = Signal()

    def __init__(self, prestamo_id: int, parent=None):
        super().__init__(parent)
        self.prestamo_id = prestamo_id
        self.setWindowTitle(f"Gestión de Préstamo #{prestamo_id}")
        self.resize(800, 700)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self.refresh_data()

        qconfig.themeChanged.connect(self.refresh_data)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(22, 22, 22, 22)
        self.main_layout.setSpacing(16)

        # 1. Top Header: Title, Client Name, Status & Scoring Badges
        header_widget = QWidget(self)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QVBoxLayout()
        self.lbl_title = TitleLabel(f"Préstamo #{self.prestamo_id}", self)
        self.lbl_cliente = CaptionLabel("Cliente: ...", self)
        self.lbl_cliente.setStyleSheet("font-size: 13px; font-weight: 500;")
        left_header.addWidget(self.lbl_title)
        left_header.addWidget(self.lbl_cliente)

        header_layout.addLayout(left_header)
        header_layout.addStretch()

        # Badges container
        badges_layout = QVBoxLayout()
        badges_layout.setAlignment(Qt.AlignRight)
        self.lbl_estado_badge = QLabel("EN_CURSO", self)
        self.lbl_estado_badge.setAlignment(Qt.AlignCenter)
        self.scoring_badge = ScoringBadge(parent=self)

        badges_layout.addWidget(self.lbl_estado_badge)
        badges_layout.addWidget(self.scoring_badge)
        header_layout.addLayout(badges_layout)

        self.main_layout.addWidget(header_widget)

        # 2. Financial Accounting Breakdown Card
        self.card_breakdown = CardWidget(self)
        card_layout = QVBoxLayout(self.card_breakdown)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        lbl_sec1 = SubtitleLabel("Desglose Contable y Liquidación", self.card_breakdown)
        card_layout.addWidget(lbl_sec1)

        # Grid of metrics
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        self.val_capital = QLabel("-", self)
        self.val_interes = QLabel("-", self)
        self.val_total_base = QLabel("-", self)
        self.val_fechas = QLabel("-", self)
        self.val_dias_mora = QLabel("-", self)
        self.val_mora_monto = QLabel("-", self)
        self.val_abonado = QLabel("-", self)
        self.val_saldo_restante = QLabel("-", self)

        def make_row(lbl_text, val_widget, r, c):
            lbl = QLabel(lbl_text, self)
            lbl.setStyleSheet(f"color: {ThemePalette.text_secondary()}; font-size: 12px; font-weight: 600;")
            val_widget.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {ThemePalette.text_primary()};")
            grid.addWidget(lbl, r * 2, c)
            grid.addWidget(val_widget, r * 2 + 1, c)

        make_row("Capital Inicial:", self.val_capital, 0, 0)
        make_row("Interés Base:", self.val_interes, 0, 1)
        make_row("Total Base a Devolver:", self.val_total_base, 0, 2)
        make_row("Plazo y Vencimiento:", self.val_fechas, 0, 3)

        make_row("Días de Atraso:", self.val_dias_mora, 1, 0)
        make_row("Interés Punitorio (Mora):", self.val_mora_monto, 1, 1)
        make_row("Total Abonado:", self.val_abonado, 1, 2)
        make_row("Saldo Restante Final:", self.val_saldo_restante, 1, 3)

        card_layout.addLayout(grid)
        self.main_layout.addWidget(self.card_breakdown)

        # 3. Actions Bar: Registrar Pago, WhatsApp, Cerrar Prestamo, Editar, Eliminar
        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        self.btn_add_pago = PrimaryPushButton(FluentIcon.ADD, "Registrar Pago", self)
        self.btn_add_pago.clicked.connect(self._open_add_payment)

        self.btn_whatsapp = PushButton(FluentIcon.CHAT, "Enviar WhatsApp", self)
        self.btn_whatsapp.clicked.connect(self._send_whatsapp_action)

        self.btn_terminar = PushButton(FluentIcon.ACCEPT, "Marcar como Terminado", self)
        self.btn_terminar.clicked.connect(self._close_loan_action)

        self.btn_edit = PushButton(FluentIcon.EDIT, "Editar", self)
        self.btn_edit.clicked.connect(self._edit_loan_action)

        self.btn_delete = PushButton(FluentIcon.DELETE, "Eliminar", self)
        self.btn_delete.setStyleSheet("color: #DC2626;")
        self.btn_delete.clicked.connect(self._delete_loan_action)

        actions_bar.addWidget(self.btn_add_pago)
        actions_bar.addWidget(self.btn_whatsapp)
        actions_bar.addWidget(self.btn_terminar)
        actions_bar.addWidget(self.btn_edit)
        actions_bar.addWidget(self.btn_delete)
        actions_bar.addStretch()

        self.main_layout.addLayout(actions_bar)

        # 4. Payments History Section
        lbl_pagos_title = SubtitleLabel("Historial de Pagos y Amortizaciones", self)
        self.main_layout.addWidget(lbl_pagos_title)

        self.payments_table = QTableWidget(self)
        self.payments_table.setColumnCount(5)
        self.payments_table.setHorizontalHeaderLabels(["ID", "Fecha y Hora", "Monto", "Método", "Comprobante / Ref"])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.payments_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.payments_table.setAlternatingRowColors(True)
        self.payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.main_layout.addWidget(self.payments_table)

    def refresh_data(self):
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                return

            cliente = p.cliente
            calc = calcular_prestamo(p)
            scoring = evaluar_cliente(cliente) if cliente else None
            is_dark = ThemePalette.is_dark()
            fg_main = QColor("#F8FAFC") if is_dark else QColor("#0F172A")

            # Update Labels
            self.lbl_cliente.setText(f"Cliente: {cliente.nombre_completo} | Tel: {cliente.telefono} | Alta: {cliente.fecha_alta[:10]}")
            if scoring:
                self.scoring_badge.set_scoring(scoring)

            # Estado Badge with adaptive contrast
            if p.estado == "TERMINADO":
                c = ThemePalette.get_status_pill("TERMINADO")
                self.lbl_estado_badge.setText("TERMINADO")
                self.lbl_estado_badge.setStyleSheet(f"""
                    background-color: {c['bg']};
                    color: {c['text']};
                    border: 2px solid {c['border']};
                    border-radius: 9px;
                    padding: 3px 14px;
                    font-size: 11px;
                    font-weight: 800;
                """)
                self.btn_terminar.setEnabled(False)
                self.btn_terminar.setText("Préstamo Ya Terminado")
            else:
                if calc.dias_atraso > 0:
                    c = ThemePalette.get_status_pill("MORA")
                    self.lbl_estado_badge.setText("EN MORA")
                else:
                    c = ThemePalette.get_status_pill("AL_DIA")
                    self.lbl_estado_badge.setText("AL DÍA")

                self.lbl_estado_badge.setStyleSheet(f"""
                    background-color: {c['bg']};
                    color: {c['text']};
                    border: 2px solid {c['border']};
                    border-radius: 9px;
                    padding: 3px 14px;
                    font-size: 11px;
                    font-weight: 800;
                """)
                self.btn_terminar.setEnabled(True)
                self.btn_terminar.setText("Marcar como Terminado")

            # Update Financial Metrics
            self.val_capital.setText(f"{CURRENCY_SYMBOL}{calc.monto_prestado:,.2f}")
            self.val_interes.setText(f"{calc.porcentaje_interes:.1f}% ({CURRENCY_SYMBOL}{calc.interes_monto:,.2f})")
            self.val_total_base.setText(f"{CURRENCY_SYMBOL}{calc.total_base:,.2f}")
            self.val_fechas.setText(f"{p.duracion_plazo} {p.tipo_plazo.lower()} (Vence {p.fecha_fin})")

            # High-contrast colors for mora and balance
            color_mora = "#FB7185" if is_dark else "#B91C1C"
            color_success = "#4ADE80" if is_dark else "#15803D"
            color_danger = "#F87171" if is_dark else "#B91C1C"

            if calc.dias_atraso > 0:
                self.val_dias_mora.setText(f"{calc.dias_atraso} días")
                self.val_dias_mora.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {color_mora};")
                self.val_mora_monto.setText(f"{CURRENCY_SYMBOL}{calc.mora_acumulada:,.2f} ({calc.tasa_mora_diaria}%/día)")
                self.val_mora_monto.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {color_mora};")
            else:
                self.val_dias_mora.setText("0 días (Al día)")
                self.val_dias_mora.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {ThemePalette.text_primary()};")
                self.val_mora_monto.setText(f"{CURRENCY_SYMBOL}0.00")
                self.val_mora_monto.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {ThemePalette.text_primary()};")

            self.val_abonado.setText(f"{CURRENCY_SYMBOL}{calc.total_abonado:,.2f}")

            if calc.saldo_restante <= 0.01:
                self.val_saldo_restante.setText(f"{CURRENCY_SYMBOL}0.00 (Saldado)")
                self.val_saldo_restante.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {color_success};")
            else:
                self.val_saldo_restante.setText(f"{CURRENCY_SYMBOL}{calc.saldo_restante:,.2f}")
                self.val_saldo_restante.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {color_danger};")

            # Populate Payments Table with high-contrast text
            pagos = list(p.pagos)
            self.payments_table.setRowCount(len(pagos))
            for i, pago in enumerate(pagos):
                it_id = QTableWidgetItem(str(pago.id))
                it_fecha = QTableWidgetItem(str(pago.fecha_pago))
                it_monto = QTableWidgetItem(f"{CURRENCY_SYMBOL}{pago.monto:,.2f}")
                it_metodo = QTableWidgetItem(pago.metodo_pago or "Efectivo")
                it_ref = QTableWidgetItem(pago.comprobante_ref or "-")

                for it in [it_id, it_fecha, it_monto, it_metodo, it_ref]:
                    it.setForeground(QBrush(fg_main))

                self.payments_table.setItem(i, 0, it_id)
                self.payments_table.setItem(i, 1, it_fecha)
                self.payments_table.setItem(i, 2, it_monto)
                self.payments_table.setItem(i, 3, it_metodo)
                self.payments_table.setItem(i, 4, it_ref)

    def _open_add_payment(self):
        dlg = PaymentDialog(self.prestamo_id, parent=self)
        if dlg.exec():
            self.refresh_data()
            self.data_changed.emit()

    def _send_whatsapp_action(self):
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p or not p.cliente:
                return
            tel = p.cliente.telefono
            if not tel:
                InfoBar.warning("Sin Teléfono", "El cliente no posee un número de teléfono registrado.", parent=self)
                return
            msg = redactar_mensaje_cobro(p.cliente, p)
            abrir_whatsapp(tel, msg)

    def _close_loan_action(self):
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                return

            calc = calcular_prestamo(p)
            if calc.saldo_restante > 0.01:
                reply = QMessageBox.question(
                    self,
                    "Confirmar Cierre con Saldo Pendiente (Condonación)",
                    f"El préstamo aún tiene un saldo restante de {CURRENCY_SYMBOL}{calc.saldo_restante:,.2f}.\n\n"
                    f"¿Desea condonar el remanente y marcarlo definitivamente como TERMINADO?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            p.estado = "TERMINADO"
            session.commit()

        InfoBar.success("Préstamo Terminado", "El préstamo ha sido cerrado con éxito.", parent=self)
        self.refresh_data()
        self.data_changed.emit()

    def _edit_loan_action(self):
        dlg = LoanEditDialog(self.prestamo_id, parent=self)
        dlg.loan_edited.connect(self._on_loan_edited)
        dlg.exec()

    def _on_loan_edited(self, prestamo_id: int):
        self.refresh_data()
        self.data_changed.emit()

    def _delete_loan_action(self):
        msg_box = MessageBox(
            "Confirmar Eliminación de Préstamo",
            f"¿Está seguro? Esta acción no se puede deshacer.\n\n"
            f"Se eliminará permanentemente el préstamo #{self.prestamo_id} y en cascada todos sus pagos asociados.",
            self
        )
        msg_box.yesButton.setText("Sí")
        msg_box.cancelButton.setText("No")
        if msg_box.exec():
            with get_session() as session:
                p = session.get(Prestamo, self.prestamo_id)
                if p:
                    session.delete(p)
                    session.commit()

            self.data_changed.emit()
            self.accept()
