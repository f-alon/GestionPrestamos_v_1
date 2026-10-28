from datetime import datetime
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QCheckBox
)
from qfluentwidgets import (
    DateTimeEdit, ComboBox, LineEdit, PushButton, PrimaryPushButton,
    InfoBar, InfoBarPosition, SubtitleLabel, BodyLabel, CaptionLabel
)
from database import get_session, Prestamo, Pago
from config import DATETIME_FORMAT, CURRENCY_SYMBOL
from services.financial_service import calcular_prestamo
from services.notification_service import redactar_comprobante_pago, abrir_whatsapp
from ui.components.custom_spinbox import CurrencySpinBox
from ui.theme import ThemePalette


class PaymentDialog(QDialog):
    """Dialog to record an amortization or partial/total payment."""
    payment_saved = Signal(int)

    def __init__(self, prestamo_id: int, parent=None):
        super().__init__(parent)
        self.prestamo_id = prestamo_id
        self.setWindowTitle(f"Registrar Pago - Préstamo #{prestamo_id}")
        self.setFixedSize(500, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._load_loan_summary()
        self._init_ui()

    def _load_loan_summary(self):
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                raise ValueError("Préstamo no encontrado")
            self.calc = calcular_prestamo(p)
            self.cliente_nombre = p.cliente.nombre_completo if p.cliente else "N/A"
            self.cliente_telefono = p.cliente.telefono if p.cliente else ""

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Info Banner
        header = SubtitleLabel(f"Registrar Abono - {self.cliente_nombre}", self)
        layout.addWidget(header)

        saldo_color = "#FB7185" if ThemePalette.is_dark() else "#DC2626"
        saldo_info = BodyLabel(
            f"Saldo restante a pagar: <b style='color:{saldo_color};'>{CURRENCY_SYMBOL}{self.calc.saldo_restante:,.2f}</b> "
            f"(Total base: {CURRENCY_SYMBOL}{self.calc.total_base:,.2f} | Mora: {CURRENCY_SYMBOL}{self.calc.mora_acumulada:,.2f})",
            self
        )
        layout.addWidget(saldo_info)

        # Form layout
        form = QFormLayout()
        form.setSpacing(12)

        # Monto input with CurrencySpinBox and Max helper button
        monto_container = QHBoxLayout()
        self.monto_spin = CurrencySpinBox(self)
        self.monto_spin.setValue(self.calc.saldo_restante if self.calc.saldo_restante > 0 else 100.0)
        monto_container.addWidget(self.monto_spin, 1)

        self.btn_pay_all = PushButton("Saldo Total", self)
        self.btn_pay_all.setToolTip("Cargar el monto total adeudado")
        self.btn_pay_all.clicked.connect(lambda: self.monto_spin.setValue(self.calc.saldo_restante))
        monto_container.addWidget(self.btn_pay_all)
        form.addRow("Monto a Pagar *:", monto_container)

        # Fecha y hora
        self.fecha_edit = DateTimeEdit(self)
        self.fecha_edit.setDateTime(QDateTime.currentDateTime())
        form.addRow("Fecha y Hora:", self.fecha_edit)

        # Metodo de pago
        self.metodo_combo = ComboBox(self)
        self.metodo_combo.addItems(["Efectivo", "Transferencia Bancaria", "Mercado Pago", "Tarjeta", "Otro"])
        form.addRow("Método de Pago:", self.metodo_combo)

        # Comprobante / Referencia
        self.comprobante_input = LineEdit(self)
        self.comprobante_input.setPlaceholderText("Ej: Transf #9821734 o Recibo #042")
        form.addRow("Comprobante / Ref:", self.comprobante_input)

        layout.addLayout(form)

        # WhatsApp Checkbox
        self.whatsapp_check = QCheckBox("Enviar recibo/comprobante por WhatsApp tras guardar", self)
        self.whatsapp_check.setChecked(bool(self.cliente_telefono))
        layout.addWidget(self.whatsapp_check)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = PushButton("Cancelar", self)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = PrimaryPushButton("Confirmar Pago", self)
        self.save_btn.clicked.connect(self._save_payment)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def _save_payment(self):
        monto = self.monto_spin.value()
        if monto <= 0.0:
            InfoBar.warning("Monto Inválido", "El monto a registrar debe ser mayor a 0.", parent=self, position=InfoBarPosition.TOP)
            return

        fecha_pago_str = self.fecha_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        metodo = self.metodo_combo.currentText()
        comprobante = self.comprobante_input.text().strip() or None

        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                return

            nuevo_pago = Pago(
                prestamo_id=p.id,
                monto=monto,
                fecha_pago=fecha_pago_str,
                metodo_pago=metodo,
                comprobante_ref=comprobante
            )
            session.add(nuevo_pago)
            session.flush()

            calc_after = calcular_prestamo(p)
            if calc_after.saldo_restante <= 0.01:
                p.estado = "TERMINADO"

            pago_id = nuevo_pago.id
            cliente_obj = p.cliente
            tel = cliente_obj.telefono if cliente_obj else ""

            if self.whatsapp_check.isChecked() and tel:
                msg = redactar_comprobante_pago(cliente_obj, p, nuevo_pago)
                abrir_whatsapp(tel, msg)

        self.payment_saved.emit(pago_id)
        self.accept()
