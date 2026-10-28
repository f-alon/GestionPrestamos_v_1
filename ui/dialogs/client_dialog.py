import re
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel
)
from qfluentwidgets import (
    LineEdit, TextEdit, PushButton, PrimaryPushButton, FluentIcon,
    InfoBar, InfoBarPosition, SubtitleLabel, CaptionLabel, MessageBox
)
from database import get_session, Cliente
from config import DATETIME_FORMAT


class ClientDialog(QDialog):
    """Dialog to create or edit a client with theme-adaptive controls and delete action."""
    client_saved = Signal(int)

    def __init__(self, client_id: int = None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle("Nuevo Cliente" if not client_id else "Editar Cliente")
        self.setFixedSize(480, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        if self.client_id:
            self._load_client_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        title_text = "Registro de Nuevo Cliente" if not self.client_id else "Modificar Datos de Cliente"
        header = SubtitleLabel(title_text, self)
        main_layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignLeft)

        self.nombre_input = LineEdit(self)
        self.nombre_input.setPlaceholderText("Ej: Juan")

        self.apellido_input = LineEdit(self)
        self.apellido_input.setPlaceholderText("Ej: Pérez")

        self.telefono_input = LineEdit(self)
        self.telefono_input.setPlaceholderText("Ej: 5491112345678 (formato internacional)")
        self.phone_hint = CaptionLabel("Solo dígitos con código de país (sin '+' ni espacios)", self)

        self.email_input = LineEdit(self)
        self.email_input.setPlaceholderText("Ej: cliente@correo.com (opcional)")

        self.notas_input = TextEdit(self)
        self.notas_input.setPlaceholderText("Observaciones o notas adicionales...")
        self.notas_input.setFixedHeight(75)

        form.addRow("Nombre *:", self.nombre_input)
        form.addRow("Apellido *:", self.apellido_input)
        form.addRow("Teléfono (WhatsApp) *:", self.telefono_input)
        form.addRow("", self.phone_hint)
        form.addRow("Email:", self.email_input)
        form.addRow("Notas:", self.notas_input)

        main_layout.addLayout(form)
        main_layout.addStretch()

        btn_layout = QHBoxLayout()

        if self.client_id:
            self.delete_btn = PushButton(FluentIcon.DELETE, "Eliminar Cliente", self)
            self.delete_btn.setStyleSheet("""
                PushButton:hover {
                    color: #DC2626;
                    border: 1px solid #EF4444;
                }
            """)
            self.delete_btn.clicked.connect(self._delete_client)
            btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()

        self.cancel_btn = PushButton("Cancelar", self)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = PrimaryPushButton("Guardar Cliente", self)
        self.save_btn.clicked.connect(self._save_client)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

    def _load_client_data(self):
        with get_session() as session:
            c = session.get(Cliente, self.client_id)
            if c:
                self.nombre_input.setText(c.nombre)
                self.apellido_input.setText(c.apellido)
                self.telefono_input.setText(c.telefono)
                self.email_input.setText(c.email or "")
                self.notas_input.setPlainText(c.notas or "")

    def _delete_client(self):
        with get_session() as session:
            c = session.get(Cliente, self.client_id)
            if not c:
                return
            nombre = c.nombre_completo
            cant_prestamos = len(c.prestamos)

        msg_box = MessageBox(
            "Confirmar Eliminación",
            f"¿Está seguro de que desea eliminar al cliente {nombre}?\n\n"
            f"⚠️ Esta acción es permanente y eliminará también {cant_prestamos} préstamo(s) y sus pagos.",
            self.window()
        )
        msg_box.yesButton.setText("Sí")
        msg_box.cancelButton.setText("No")

        if msg_box.exec():
            with get_session() as session:
                c = session.get(Cliente, self.client_id)
                if c:
                    session.delete(c)
            self.client_saved.emit(-1)
            self.accept()

    def _save_client(self):
        nombre = self.nombre_input.text().strip()
        apellido = self.apellido_input.text().strip()
        telefono = re.sub(r"[^\d]", "", self.telefono_input.text().strip())
        email = self.email_input.text().strip() or None
        notas = self.notas_input.toPlainText().strip() or None

        if not nombre:
            InfoBar.warning("Campo Requerido", "Por favor ingresa el nombre del cliente.", parent=self, position=InfoBarPosition.TOP)
            self.nombre_input.setFocus()
            return

        if not apellido:
            InfoBar.warning("Campo Requerido", "Por favor ingresa el apellido del cliente.", parent=self, position=InfoBarPosition.TOP)
            self.apellido_input.setFocus()
            return

        if not telefono or len(telefono) < 8:
            InfoBar.warning(
                "Teléfono Inválido",
                "Ingresa un número telefónico válido con código internacional (mínimo 8 dígitos).",
                parent=self,
                position=InfoBarPosition.TOP
            )
            self.telefono_input.setFocus()
            return

        with get_session() as session:
            if self.client_id:
                c = session.get(Cliente, self.client_id)
                if not c:
                    return
                c.nombre = nombre
                c.apellido = apellido
                c.telefono = telefono
                c.email = email
                c.notas = notas
                saved_id = c.id
            else:
                c = Cliente(
                    nombre=nombre,
                    apellido=apellido,
                    telefono=telefono,
                    email=email,
                    notas=notas,
                    fecha_alta=datetime.now().strftime(DATETIME_FORMAT)
                )
                session.add(c)
                session.flush()
                saved_id = c.id

        self.client_saved.emit(saved_id)
        self.accept()
