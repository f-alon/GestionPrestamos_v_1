from datetime import date, datetime, timedelta
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget
)
from qfluentwidgets import (
    ComboBox, PrimaryPushButton, PushButton, FluentIcon, InfoBar, InfoBarPosition,
    CardWidget, TitleLabel, SubtitleLabel, CaptionLabel, qconfig
)
from database import get_session, Prestamo
from config import CURRENCY_SYMBOL, DATE_FORMAT
from services.financial_service import calcular_prestamo
from ui.components.custom_spinbox import (
    CurrencySpinBox, PercentSpinBox, IntegerSpinBox, CustomDateEdit
)
from ui.theme import ThemePalette


class LoanEditDialog(QDialog):
    """
    Modal dialog to edit loan parameters (amount, interest, terms, dates, penalty rate, status).
    Includes real-time recalculation preview and high-contrast WCAG styling.
    """
    loan_edited = Signal(int)

    def __init__(self, prestamo_id: int, parent=None):
        super().__init__(parent)
        self.prestamo_id = prestamo_id
        self._is_updating = False

        self.setWindowTitle(f"Editar Préstamo #{prestamo_id}")
        self.resize(720, 680)
        self.setMinimumWidth(640)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._load_loan_data()
        self._recalculate_preview()

        qconfig.themeChanged.connect(self._recalculate_preview)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header_layout = QVBoxLayout()
        self.title_lbl = TitleLabel(f"Modificar Préstamo #{self.prestamo_id}", self)
        self.subtitle_lbl = CaptionLabel("Corrija montos, fechas, plazos o tasas del préstamo.", self)
        self.subtitle_lbl.setStyleSheet("font-size: 13px;")
        self.client_info_lbl = CaptionLabel("Cliente: Cargando...", self)
        self.client_info_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {ThemePalette.accent_primary()};")

        header_layout.addWidget(self.title_lbl)
        header_layout.addWidget(self.subtitle_lbl)
        header_layout.addWidget(self.client_info_lbl)
        layout.addLayout(header_layout)

        # Form Card
        form_card = CardWidget(self)
        form_layout = QGridLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(14)

        # Capital Prestado
        lbl_monto = QLabel("Monto Prestado (Capital):", form_card)
        lbl_monto.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.spin_monto = CurrencySpinBox(form_card)
        self.spin_monto.setRange(1.0, 999999999.0)
        self.spin_monto.setValue(100000.0)
        self.spin_monto.valueChanged.connect(self._on_input_changed)
        form_layout.addWidget(lbl_monto, 0, 0)
        form_layout.addWidget(self.spin_monto, 1, 0)

        # Porcentaje Interés
        lbl_interes = QLabel("Tasa de Interés Total (%):", form_card)
        lbl_interes.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.spin_interes = PercentSpinBox(form_card)
        self.spin_interes.setRange(0.0, 1000.0)
        self.spin_interes.setValue(20.0)
        self.spin_interes.valueChanged.connect(self._on_input_changed)
        form_layout.addWidget(lbl_interes, 0, 1)
        form_layout.addWidget(self.spin_interes, 1, 1)

        # Plazo Tipo y Duración
        lbl_plazo = QLabel("Plazo:", form_card)
        lbl_plazo.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        plazo_box = QHBoxLayout()
        self.spin_duracion = IntegerSpinBox(form_card)
        self.spin_duracion.setRange(1, 3650)
        self.spin_duracion.setValue(30)
        self.spin_duracion.valueChanged.connect(self._on_duration_changed)

        self.combo_tipo_plazo = ComboBox(form_card)
        self.combo_tipo_plazo.addItem("Días", "DIAS")
        self.combo_tipo_plazo.addItem("Semanas", "SEMANAS")
        self.combo_tipo_plazo.currentIndexChanged.connect(self._on_duration_changed)

        plazo_box.addWidget(self.spin_duracion)
        plazo_box.addWidget(self.combo_tipo_plazo)
        form_layout.addWidget(lbl_plazo, 2, 0)
        form_layout.addLayout(plazo_box, 3, 0)

        # Tasa Mora Diaria
        lbl_mora = QLabel("Tasa de Mora Diaria (%):", form_card)
        lbl_mora.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.spin_mora = PercentSpinBox(form_card)
        self.spin_mora.setRange(0.0, 100.0)
        self.spin_mora.setValue(1.0)
        self.spin_mora.valueChanged.connect(self._on_input_changed)
        form_layout.addWidget(lbl_mora, 2, 1)
        form_layout.addWidget(self.spin_mora, 3, 1)

        # Fecha Inicio
        lbl_inicio = QLabel("Fecha de Inicio:", form_card)
        lbl_inicio.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.date_inicio = CustomDateEdit(form_card)
        self.date_inicio.setDisplayFormat("yyyy-MM-dd")
        self.date_inicio.dateChanged.connect(self._on_duration_changed)
        form_layout.addWidget(lbl_inicio, 4, 0)
        form_layout.addWidget(self.date_inicio, 5, 0)

        # Fecha Fin
        lbl_fin = QLabel("Fecha de Vencimiento:", form_card)
        lbl_fin.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.date_fin = CustomDateEdit(form_card)
        self.date_fin.setDisplayFormat("yyyy-MM-dd")
        self.date_fin.dateChanged.connect(self._on_input_changed)
        form_layout.addWidget(lbl_fin, 4, 1)
        form_layout.addWidget(self.date_fin, 5, 1)

        # Estado del Préstamo
        lbl_estado = QLabel("Estado del Préstamo:", form_card)
        lbl_estado.setStyleSheet(f"font-weight: 600; color: {ThemePalette.text_primary()};")
        self.combo_estado = ComboBox(form_card)
        self.combo_estado.addItem("EN_CURSO (Activo)", "EN_CURSO")
        self.combo_estado.addItem("TERMINADO (Cerrado)", "TERMINADO")
        self.combo_estado.currentIndexChanged.connect(self._on_input_changed)
        form_layout.addWidget(lbl_estado, 6, 0)
        form_layout.addWidget(self.combo_estado, 7, 0)

        layout.addWidget(form_card)

        # Live Summary Card
        self.preview_card = CardWidget(self)
        prev_layout = QVBoxLayout(self.preview_card)
        prev_layout.setContentsMargins(18, 14, 18, 14)
        prev_layout.setSpacing(10)

        lbl_prev_title = SubtitleLabel("Recálculo Contable Estimado", self.preview_card)
        prev_layout.addWidget(lbl_prev_title)

        grid_prev = QGridLayout()
        grid_prev.setHorizontalSpacing(20)
        grid_prev.setVerticalSpacing(6)

        self.prev_base = QLabel("-", self.preview_card)
        self.prev_interes_monto = QLabel("-", self.preview_card)
        self.prev_vencimiento = QLabel("-", self.preview_card)
        self.prev_saldo = QLabel("-", self.preview_card)

        def add_metric(label_text, widget, r, c):
            l = QLabel(label_text, self.preview_card)
            l.setStyleSheet(f"color: {ThemePalette.text_secondary()}; font-size: 11px; font-weight: 600;")
            widget.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {ThemePalette.text_primary()};")
            grid_prev.addWidget(l, r * 2, c)
            grid_prev.addWidget(widget, r * 2 + 1, c)

        add_metric("Capital + Interés:", self.prev_base, 0, 0)
        add_metric("Ganancia Estimada:", self.prev_interes_monto, 0, 1)
        add_metric("Fecha de Vencimiento:", self.prev_vencimiento, 0, 2)
        add_metric("Saldo Restante Proyectado:", self.prev_saldo, 0, 3)

        prev_layout.addLayout(grid_prev)
        layout.addWidget(self.preview_card)

        # Buttons Bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = PushButton("Cancelar", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = PrimaryPushButton(FluentIcon.SAVE, "Guardar Cambios", self)
        self.btn_save.clicked.connect(self._save_changes)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _load_loan_data(self):
        self._is_updating = True
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                InfoBar.error("Error", "No se encontró el préstamo a editar.", parent=self)
                self.reject()
                return

            if p.cliente:
                self.client_info_lbl.setText(f"Cliente: {p.cliente.nombre_completo} | Tel: {p.cliente.telefono}")

            self.spin_monto.setValue(p.monto_prestado)
            self.spin_interes.setValue(p.porcentaje_interes)
            self.spin_duracion.setValue(p.duracion_plazo)

            idx_tipo = self.combo_tipo_plazo.findData(p.tipo_plazo)
            if idx_tipo >= 0:
                self.combo_tipo_plazo.setCurrentIndex(idx_tipo)

            self.spin_mora.setValue(p.tasa_mora_diaria)

            # Dates
            try:
                d_ini = datetime.strptime(p.fecha_inicio, DATE_FORMAT).date()
                self.date_inicio.setDate(QDate(d_ini.year, d_ini.month, d_ini.day))
            except Exception:
                self.date_inicio.setDate(QDate.currentDate())

            try:
                d_fin = datetime.strptime(p.fecha_fin, DATE_FORMAT).date()
                self.date_fin.setDate(QDate(d_fin.year, d_fin.month, d_fin.day))
            except Exception:
                self.date_fin.setDate(QDate.currentDate().addDays(30))

            idx_estado = self.combo_estado.findData(p.estado)
            if idx_estado >= 0:
                self.combo_estado.setCurrentIndex(idx_estado)

        self._is_updating = False

    def _on_duration_changed(self):
        if self._is_updating:
            return
        # Calculate new end date based on duration and type
        q_ini = self.date_inicio.date()
        ini_date = date(q_ini.year(), q_ini.month(), q_ini.day())
        duracion = self.spin_duracion.value()
        tipo = self.combo_tipo_plazo.currentData() or "DIAS"

        if tipo == "SEMANAS":
            fin_date = ini_date + timedelta(weeks=duracion)
        else:
            fin_date = ini_date + timedelta(days=duracion)

        self._is_updating = True
        self.date_fin.setDate(QDate(fin_date.year, fin_date.month, fin_date.day))
        self._is_updating = False

        self._recalculate_preview()

    def _on_input_changed(self):
        if self._is_updating:
            return
        self._recalculate_preview()

    def _recalculate_preview(self):
        monto = self.spin_monto.value()
        interes_pct = self.spin_interes.value()
        interes_monto = monto * (interes_pct / 100.0)
        total_base = monto + interes_monto

        q_fin = self.date_fin.date()
        fin_date = date(q_fin.year(), q_fin.month(), q_fin.day())
        q_ini = self.date_inicio.date()
        ini_date = date(q_ini.year(), q_ini.month(), q_ini.day())

        # Check payments already made on this loan
        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            total_abonado = sum(pago.monto for pago in p.pagos) if p else 0.0

        # Calculate estimated mora
        hoy = date.today()
        estado = self.combo_estado.currentData() or "EN_CURSO"
        dias_diferencia = (hoy - fin_date).days
        dias_atraso = dias_diferencia if (estado == "EN_CURSO" and dias_diferencia > 0) else 0

        saldo_base_pendiente = max(0.0, total_base - total_abonado)
        tasa_mora = self.spin_mora.value()
        mora_acumulada = saldo_base_pendiente * (tasa_mora / 100.0) * dias_atraso
        saldo_restante = max(0.0, (total_base + mora_acumulada) - total_abonado)

        self.prev_base.setText(f"{CURRENCY_SYMBOL}{total_base:,.2f}")
        self.prev_interes_monto.setText(f"{CURRENCY_SYMBOL}{interes_monto:,.2f}")
        self.prev_vencimiento.setText(fin_date.strftime(DATE_FORMAT))
        self.prev_saldo.setText(f"{CURRENCY_SYMBOL}{saldo_restante:,.2f}")

    def _save_changes(self):
        q_ini = self.date_inicio.date()
        q_fin = self.date_fin.date()
        fecha_inicio_str = f"{q_ini.year():04d}-{q_ini.month():02d}-{q_ini.day():02d}"
        fecha_fin_str = f"{q_fin.year():04d}-{q_fin.month():02d}-{q_fin.day():02d}"

        if q_fin < q_ini:
            InfoBar.warning(
                "Fecha Inválida",
                "La fecha de vencimiento no puede ser anterior a la fecha de inicio.",
                parent=self,
                duration=4000
            )
            return

        monto = self.spin_monto.value()
        if monto <= 0:
            InfoBar.warning("Monto Inválido", "El monto prestado debe ser mayor a cero.", parent=self)
            return

        with get_session() as session:
            p = session.get(Prestamo, self.prestamo_id)
            if not p:
                InfoBar.error("Error", "No se encontró el préstamo.", parent=self)
                return

            p.monto_prestado = monto
            p.porcentaje_interes = self.spin_interes.value()
            p.tipo_plazo = self.combo_tipo_plazo.currentData() or "DIAS"
            p.duracion_plazo = self.spin_duracion.value()
            p.fecha_inicio = fecha_inicio_str
            p.fecha_fin = fecha_fin_str
            p.tasa_mora_diaria = self.spin_mora.value()
            p.estado = self.combo_estado.currentData() or "EN_CURSO"

            session.commit()

        self.loan_edited.emit(self.prestamo_id)
        self.accept()
