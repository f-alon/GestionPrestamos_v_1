import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFormLayout,
    QFrame
)
from qfluentwidgets import (
    EditableComboBox, ComboBox,
    PrimaryPushButton, PushButton, ToolButton, CardWidget, FluentIcon,
    InfoBar, InfoBarPosition, TitleLabel, SubtitleLabel, CaptionLabel,
    BodyLabel, StrongBodyLabel, qconfig
)
from database import get_session, Cliente, Prestamo
from config import (
    CURRENCY_SYMBOL, DEFAULT_INTEREST_RATE, DEFAULT_DAILY_MORA_RATE,
    DEFAULT_TERM_TYPE, DEFAULT_TERM_DURATION, DATE_FORMAT
)
from services.financial_service import simular_prestamo, calcular_fecha_fin
from services.scoring_service import evaluar_cliente, ScoringResult
from ui.dialogs.client_dialog import ClientDialog
from ui.components.scoring_badge import ScoringBadge
from ui.components.custom_spinbox import (
    CurrencySpinBox,
    PercentSpinBox,
    IntegerSpinBox,
    CustomDateEdit
)
from ui.theme import ThemePalette


def _normalize_str(text: str) -> str:
    """Removes accents and lowercases for forgiving fuzzy searches."""
    if not text:
        return ""
    clean = unicodedata.normalize("NFD", text)
    return "".join(c for c in clean if unicodedata.category(c) != "Mn").lower().strip()


class NewLoanView(QWidget):
    """
    View for registering a new loan with:
    - Smart autocomplete client selector with accent-insensitive search
    - Instant automatic credit scoring evaluation & alert banner display
    - Large-format currency input supporting values from $ 100 up to $ 1,000,000,000.00
    - Wide CustomDateEdit components for start date and end date
    - Real-time side summary panel updating live
    - High-contrast typography and theme adaptation
    """
    loan_created = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clients_cache = []
        self._selected_client_id: Optional[int] = None

        self._init_ui()
        self.reload_clients()
        self._recalculate_preview()

        qconfig.themeChanged.connect(self._on_theme_changed)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header with Fluent Typography
        self.header_title = TitleLabel("Alta de Préstamo", self)
        self.header_subtitle = CaptionLabel("Complete los datos financieros del nuevo crédito y verifique la evaluación crediticia.", self)
        self.header_subtitle.setStyleSheet("font-size: 13px;")
        main_layout.addWidget(self.header_title)
        main_layout.addWidget(self.header_subtitle)

        # Alert Banner for Client Scoring (Red alert for morosos)
        self.alert_banner = QFrame(self)
        self.alert_banner.setObjectName("alertBanner")
        banner_layout = QHBoxLayout(self.alert_banner)
        banner_layout.setContentsMargins(16, 12, 16, 12)
        self.lbl_alert_icon = QLabel("⚠️", self.alert_banner)
        self.lbl_alert_icon.setStyleSheet("font-size: 18px;")
        self.lbl_alert_text = QLabel("Atención: El cliente registra antecedentes de mora.", self.alert_banner)
        banner_layout.addWidget(self.lbl_alert_icon)
        banner_layout.addWidget(self.lbl_alert_text, 1)
        self.alert_banner.hide()
        main_layout.addWidget(self.alert_banner)

        # Content split: Form on Left, Dynamic Preview Panel on Right
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # LEFT: Form Card
        self.card_form = CardWidget(self)
        form_card_layout = QVBoxLayout(self.card_form)
        form_card_layout.setContentsMargins(22, 22, 22, 22)
        form_card_layout.setSpacing(16)

        form_title = SubtitleLabel("Datos de la Operación", self.card_form)
        form_card_layout.addWidget(form_title)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)

        def make_field_label(text: str) -> QLabel:
            lbl = QLabel(text, self)
            lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {ThemePalette.text_primary()};")
            return lbl

        # 1. Cliente selector + '+' button
        client_row = QHBoxLayout()
        self.client_combo = EditableComboBox(self)
        self.client_combo.setPlaceholderText("Buscar cliente por nombre o teléfono...")
        self.client_combo.setMinimumWidth(260)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        self.client_combo.textChanged.connect(self._on_client_changed)
        client_row.addWidget(self.client_combo, stretch=1)

        self.btn_new_client = ToolButton(FluentIcon.ADD, self)
        self.btn_new_client.setToolTip("Crear nuevo cliente al vuelo")
        self.btn_new_client.clicked.connect(self._open_new_client_dialog)
        client_row.addWidget(self.btn_new_client)

        form.addRow(make_field_label("Cliente *:"), client_row)

        # Client scoring status row
        self.scoring_widget = ScoringBadge(parent=self)
        form.addRow(make_field_label("Evaluación Crediticia:"), self.scoring_widget)

        # 2. Monto Prestado (Capital) using enhanced CurrencySpinBox
        self.monto_spin = CurrencySpinBox(self)
        self.monto_spin.setValue(10000.0)
        self.monto_spin.valueChanged.connect(self._recalculate_preview)
        form.addRow(make_field_label("Capital a Prestar *:"), self.monto_spin)

        # 3. Porcentaje Interes using PercentSpinBox
        self.interes_spin = PercentSpinBox(self)
        self.interes_spin.setValue(DEFAULT_INTEREST_RATE)
        self.interes_spin.valueChanged.connect(self._recalculate_preview)
        form.addRow(make_field_label("Tasa de Interés Base *:"), self.interes_spin)

        # 4. Tipo y Duracion de Plazo using IntegerSpinBox
        plazo_row = QHBoxLayout()
        self.duracion_spin = IntegerSpinBox(self)
        self.duracion_spin.setValue(DEFAULT_TERM_DURATION)
        self.duracion_spin.valueChanged.connect(self._on_term_params_changed)
        plazo_row.addWidget(self.duracion_spin)

        self.tipo_plazo_combo = ComboBox(self)
        self.tipo_plazo_combo.addItems(["Días", "Semanas"])
        self.tipo_plazo_combo.setCurrentText("Días" if DEFAULT_TERM_TYPE == "DIAS" else "Semanas")
        self.tipo_plazo_combo.currentIndexChanged.connect(self._on_term_params_changed)
        plazo_row.addWidget(self.tipo_plazo_combo)

        form.addRow(make_field_label("Plazo Pactado *:"), plazo_row)

        # 5. Fechas: Inicio y Fin using CustomDateEdit (Fixes cut-off text bug)
        self.fecha_inicio_edit = CustomDateEdit(self)
        self.fecha_inicio_edit.setDate(QDate.currentDate())
        self.fecha_inicio_edit.dateChanged.connect(self._on_term_params_changed)
        form.addRow(make_field_label("Fecha de Inicio:"), self.fecha_inicio_edit)

        self.fecha_fin_edit = CustomDateEdit(self)
        self.fecha_fin_edit.setDate(QDate.currentDate().addDays(DEFAULT_TERM_DURATION))
        self.fecha_fin_edit.dateChanged.connect(self._recalculate_preview)
        form.addRow(make_field_label("Fecha de Vencimiento:"), self.fecha_fin_edit)

        # 6. Tasa Mora Diaria using PercentSpinBox
        self.mora_spin = PercentSpinBox(self)
        self.mora_spin.setRange(0.0, 50.0)
        self.mora_spin.setValue(DEFAULT_DAILY_MORA_RATE)
        self.mora_spin.setSuffix(" % diario")
        self.mora_spin.valueChanged.connect(self._recalculate_preview)
        form.addRow(make_field_label("Punitorio por Mora:"), self.mora_spin)

        form_card_layout.addLayout(form)
        form_card_layout.addStretch()

        # Submit Button
        self.btn_submit = PrimaryPushButton(FluentIcon.ACCEPT, "Crear y Emitir Préstamo", self)
        self.btn_submit.setFixedHeight(42)
        self.btn_submit.clicked.connect(self._submit_loan)
        form_card_layout.addWidget(self.btn_submit)

        content_layout.addWidget(self.card_form, stretch=3)

        # RIGHT: Dynamic Live Preview Panel
        self.card_preview = CardWidget(self)
        self.card_preview.setFixedWidth(340)
        preview_layout = QVBoxLayout(self.card_preview)
        preview_layout.setContentsMargins(22, 22, 22, 22)
        preview_layout.setSpacing(14)

        prev_header = SubtitleLabel("Resumen Financiero", self.card_preview)
        prev_subtitle = CaptionLabel("Cálculo instantáneo según condiciones pactadas.", self.card_preview)
        preview_layout.addWidget(prev_header)
        preview_layout.addWidget(prev_subtitle)

        # Divider line
        line = QFrame(self.card_preview)
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {ThemePalette.card_border()};")
        preview_layout.addWidget(line)

        # Summary Metrics
        prev_grid = QGridLayout()
        prev_grid.setVerticalSpacing(12)

        self.prev_capital = StrongBodyLabel("-", self)
        self.prev_interes_monto = StrongBodyLabel("-", self)
        self.prev_total_devolver = QLabel("-", self)
        self.prev_plazo_resumen = StrongBodyLabel("-", self)
        self.prev_vencimiento_resumen = StrongBodyLabel("-", self)
        self.prev_tasa_mora = StrongBodyLabel("-", self)

        def add_preview_row(title_text, val_lbl, r):
            t_lbl = QLabel(title_text, self)
            t_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {ThemePalette.text_secondary()};")
            prev_grid.addWidget(t_lbl, r, 0)
            prev_grid.addWidget(val_lbl, r, 1, Qt.AlignRight)

        add_preview_row("Capital Prestado:", self.prev_capital, 0)
        add_preview_row("Interés Generado:", self.prev_interes_monto, 1)
        add_preview_row("Plazo Total:", self.prev_plazo_resumen, 2)
        add_preview_row("Fecha Límite:", self.prev_vencimiento_resumen, 3)
        add_preview_row("Recargo Diario Mora:", self.prev_tasa_mora, 4)

        preview_layout.addLayout(prev_grid)

        # Big Total Highlight Box
        self.total_box = QFrame(self.card_preview)
        tb_layout = QVBoxLayout(self.total_box)
        tb_layout.setContentsMargins(14, 14, 14, 14)
        self.tb_title = QLabel("TOTAL BASE A COBRAR", self.total_box)
        tb_layout.addWidget(self.tb_title)
        tb_layout.addWidget(self.prev_total_devolver)
        preview_layout.addWidget(self.total_box)

        preview_layout.addStretch()
        content_layout.addWidget(self.card_preview, stretch=2)

        main_layout.addLayout(content_layout)
        self._apply_theme_box_styles()

    def _apply_theme_box_styles(self):
        h = ThemePalette.highlight_box()
        self.total_box.setStyleSheet(f"""
            QFrame {{
                background-color: {h['bg']};
                border: 2px solid {h['border']};
                border-radius: 10px;
            }}
        """)
        self.tb_title.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {h['title']};")
        self.prev_total_devolver.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {h['text']};")

    def _on_theme_changed(self):
        self._apply_theme_box_styles()
        self._on_client_changed()

    def reload_clients(self, select_client_id: int = None):
        """Loads client list into combo box and local cache."""
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        self._clients_cache = []

        with get_session() as session:
            clients = session.query(Cliente).order_by(Cliente.apellido, Cliente.nombre).all()
            for c in clients:
                display_str = f"{c.nombre_completo} ({c.telefono})"
                self._clients_cache.append({
                    "id": c.id,
                    "nombre": c.nombre_completo,
                    "telefono": c.telefono,
                    "display": display_str
                })
                self.client_combo.addItem(display_str, userData=c.id)

        self.client_combo.blockSignals(False)

        if select_client_id:
            for idx in range(self.client_combo.count()):
                if self.client_combo.itemData(idx) == select_client_id:
                    self.client_combo.setCurrentIndex(idx)
                    break
        elif self.client_combo.count() > 0:
            self.client_combo.setCurrentIndex(0)

        self._on_client_changed()

    def _resolve_client_id(self) -> Optional[int]:
        """
        Resolves client ID using currentData() or forgiving accent-free text search.
        """
        data = self.client_combo.currentData()
        if isinstance(data, int) and data > 0:
            return data

        typed = self.client_combo.text().strip()
        if not typed:
            return None

        clean_typed = _normalize_str(typed)
        digits_typed = "".join(ch for ch in typed if ch.isdigit())

        for item in self._clients_cache:
            if clean_typed == _normalize_str(item["display"]):
                return item["id"]

        for item in self._clients_cache:
            if clean_typed in _normalize_str(item["nombre"]) or clean_typed in _normalize_str(item["display"]):
                return item["id"]

        if len(digits_typed) >= 4:
            for item in self._clients_cache:
                if digits_typed in item["telefono"]:
                    return item["id"]

        return None

    def _open_new_client_dialog(self):
        dlg = ClientDialog(parent=self)
        dlg.client_saved.connect(lambda cid: self.reload_clients(select_client_id=cid))
        dlg.exec()

    def _on_client_changed(self):
        client_id = self._resolve_client_id()
        self._selected_client_id = client_id

        if not client_id:
            self.alert_banner.hide()
            if self.client_combo.text().strip():
                self.scoring_widget.label.setText("Cliente no encontrado")
                self.scoring_widget.label.setStyleSheet("""
                    QLabel {
                        background-color: #F1F5F9;
                        color: #64748B;
                        border: 1px solid #CBD5E1;
                        border-radius: 9px;
                        padding: 3px 10px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                """)
            return

        with get_session() as session:
            cliente = session.get(Cliente, client_id)
            if not cliente:
                self.alert_banner.hide()
                return

            scoring: ScoringResult = evaluar_cliente(cliente)
            self.scoring_widget.set_scoring(scoring)

            # Display Alerta Roja banner automatically if low credit score / moroso
            if scoring.nivel == "ROJO":
                c = ThemePalette.get_scoring_colors("ROJO")
                self.alert_banner.setStyleSheet(f"""
                    QFrame#alertBanner {{
                        background-color: {c['bg']};
                        border: 2px solid {c['border']};
                        border-radius: 8px;
                    }}
                """)
                self.lbl_alert_text.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {c['text']};")
                self.lbl_alert_text.setText(scoring.mensaje)
                self.alert_banner.show()
            else:
                self.alert_banner.hide()

    def _on_term_params_changed(self):
        q_ini = self.fecha_inicio_edit.date()
        f_ini = date(q_ini.year(), q_ini.month(), q_ini.day())
        duracion = self.duracion_spin.value()
        tipo_plazo = "SEMANAS" if self.tipo_plazo_combo.currentText().upper().startswith("SEM") else "DIAS"

        f_fin = calcular_fecha_fin(f_ini, tipo_plazo, duracion)
        self.fecha_fin_edit.blockSignals(True)
        self.fecha_fin_edit.setDate(QDate(f_fin.year, f_fin.month, f_fin.day))
        self.fecha_fin_edit.blockSignals(False)

        self._recalculate_preview()

    def _recalculate_preview(self):
        monto = self.monto_spin.value()
        interes_pct = self.interes_spin.value()
        duracion = self.duracion_spin.value()
        tipo_plazo = "SEMANAS" if self.tipo_plazo_combo.currentText().upper().startswith("SEM") else "DIAS"

        q_ini = self.fecha_inicio_edit.date()
        f_ini = date(q_ini.year(), q_ini.month(), q_ini.day())

        q_fin = self.fecha_fin_edit.date()
        f_fin = date(q_fin.year(), q_fin.month(), q_fin.day())

        sim = simular_prestamo(monto, interes_pct, tipo_plazo, duracion, f_ini)

        self.prev_capital.setText(f"{CURRENCY_SYMBOL}{monto:,.2f}")
        self.prev_interes_monto.setText(f"{CURRENCY_SYMBOL}{sim['interes_monto']:,.2f} ({interes_pct:.1f}%)")
        self.prev_total_devolver.setText(f"{CURRENCY_SYMBOL}{sim['total_base']:,.2f}")
        self.prev_plazo_resumen.setText(f"{duracion} {tipo_plazo.lower()}")
        self.prev_vencimiento_resumen.setText(f_fin.strftime("%d/%m/%Y"))
        self.prev_tasa_mora.setText(f"{self.mora_spin.value():.2f}% / día")

    def _submit_loan(self):
        client_id = self._selected_client_id or self._resolve_client_id()
        if not client_id:
            InfoBar.warning("Cliente Requerido", "Debe seleccionar un cliente válido para otorgar el préstamo.", parent=self, position=InfoBarPosition.TOP)
            return

        monto = self.monto_spin.value()
        if monto <= 0:
            InfoBar.warning("Monto Inválido", "El monto prestado debe ser mayor a 0.", parent=self, position=InfoBarPosition.TOP)
            return

        interes_pct = self.interes_spin.value()
        if interes_pct < 0:
            InfoBar.warning("Interés Inválido", "El interés no puede ser negativo.", parent=self, position=InfoBarPosition.TOP)
            return

        q_ini = self.fecha_inicio_edit.date()
        f_ini = date(q_ini.year(), q_ini.month(), q_ini.day())

        q_fin = self.fecha_fin_edit.date()
        f_fin = date(q_fin.year(), q_fin.month(), q_fin.day())

        if f_fin <= f_ini:
            InfoBar.warning("Fechas Incoherentes", "La fecha de vencimiento debe ser posterior a la fecha de inicio.", parent=self, position=InfoBarPosition.TOP)
            return

        tipo_plazo = "SEMANAS" if self.tipo_plazo_combo.currentText().upper().startswith("SEM") else "DIAS"
        duracion = self.duracion_spin.value()
        mora_diaria = self.mora_spin.value()

        with get_session() as session:
            nuevo_prestamo = Prestamo(
                cliente_id=client_id,
                monto_prestado=monto,
                porcentaje_interes=interes_pct,
                tipo_plazo=tipo_plazo,
                duracion_plazo=duracion,
                fecha_inicio=f_ini.strftime(DATE_FORMAT),
                fecha_fin=f_fin.strftime(DATE_FORMAT),
                tasa_mora_diaria=mora_diaria,
                estado="EN_CURSO"
            )
            session.add(nuevo_prestamo)
            session.flush()
            prestamo_id = nuevo_prestamo.id

        InfoBar.success("Préstamo Creado", f"El préstamo #{prestamo_id} se ha registrado exitosamente.", parent=self)
        self.loan_created.emit(prestamo_id)
