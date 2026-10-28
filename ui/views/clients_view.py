from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu
)
from qfluentwidgets import (
    SearchLineEdit, PrimaryPushButton, PushButton, ToolButton, FluentIcon, InfoBar, InfoBarPosition,
    TitleLabel, CaptionLabel, MessageBox, qconfig
)
from database import get_session, Cliente, Prestamo
from services.scoring_service import evaluar_cliente
from ui.dialogs.client_dialog import ClientDialog
from ui.components.scoring_badge import ScoringBadge
from ui.theme import ThemePalette


class ClientsView(QWidget):
    """
    View to manage clients, explore credit scores, and review contact information.
    Includes explicit Delete Client action with Sí/No confirmation dialog.
    """
    client_selected = Signal(int)
    client_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clients_cache = []
        self._init_ui()
        self.refresh_clients()

        qconfig.themeChanged.connect(self._apply_filter)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # Header with Fluent Typography and Action Buttons
        header_layout = QHBoxLayout()
        header_info = QVBoxLayout()
        self.header_title = TitleLabel("Cartera de Clientes", self)
        self.header_subtitle = CaptionLabel("Gestión de contactos, historial financiero y evaluación de riesgo crediticio.", self)
        self.header_subtitle.setStyleSheet("font-size: 13px;")
        header_info.addWidget(self.header_title)
        header_info.addWidget(self.header_subtitle)
        header_layout.addLayout(header_info)
        header_layout.addStretch()

        # Action Buttons in Header
        self.btn_new = PrimaryPushButton(FluentIcon.ADD, "Nuevo Cliente", self)
        self.btn_new.clicked.connect(self._open_new_client)
        header_layout.addWidget(self.btn_new)

        self.btn_edit = PushButton(FluentIcon.EDIT, "Editar", self)
        self.btn_edit.clicked.connect(self._edit_selected_client)
        header_layout.addWidget(self.btn_edit)

        self.btn_delete = PushButton(FluentIcon.DELETE, "Eliminar Cliente", self)
        self.btn_delete.setStyleSheet("""
            PushButton:hover {
                color: #DC2626;
                border: 1px solid #EF4444;
            }
        """)
        self.btn_delete.clicked.connect(self._delete_selected_client)
        header_layout.addWidget(self.btn_delete)

        main_layout.addLayout(header_layout)

        # Filter bar
        filter_layout = QHBoxLayout()
        self.search_box = SearchLineEdit(self)
        self.search_box.setPlaceholderText("Buscar por nombre, apellido, teléfono o email...")
        self.search_box.setFixedWidth(340)
        self.search_box.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.search_box)
        filter_layout.addStretch()

        self.btn_refresh = PushButton(FluentIcon.SYNC, "Actualizar", self)
        self.btn_refresh.clicked.connect(self.refresh_clients)
        filter_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(filter_layout)

        # Table with Actions Column
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre Completo", "Teléfono (WhatsApp)", "Email", "Fecha Alta", "Préstamos", "Scoring Crediticio", "Acciones"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        main_layout.addWidget(self.table)

    def refresh_clients(self):
        with get_session() as session:
            clients = session.query(Cliente).order_by(Cliente.apellido, Cliente.nombre).all()
            self._clients_cache = []

            for c in clients:
                scoring = evaluar_cliente(c)
                activos = sum(1 for p in c.prestamos if p.estado == "EN_CURSO")
                cerrados = sum(1 for p in c.prestamos if p.estado == "TERMINADO")

                self._clients_cache.append({
                    "id": c.id,
                    "nombre": c.nombre,
                    "apellido": c.apellido,
                    "nombre_completo": c.nombre_completo,
                    "telefono": c.telefono,
                    "email": c.email or "-",
                    "fecha_alta": c.fecha_alta[:10] if c.fecha_alta else "-",
                    "prestamos_str": f"{activos} activos / {cerrados} cerrados",
                    "scoring": scoring
                })

        self._apply_filter()

    def _apply_filter(self):
        query = self.search_box.text().strip().lower()
        filtered = []

        for c in self._clients_cache:
            if query:
                match = (
                    query in str(c["id"]) or
                    query in c["nombre_completo"].lower() or
                    query in c["telefono"] or
                    query in c["email"].lower()
                )
                if not match:
                    continue
            filtered.append(c)

        is_dark = ThemePalette.is_dark()
        fg_main = QBrush(QColor("#F8FAFC") if is_dark else QColor("#0F172A"))
        font_bold = QFont()
        font_bold.setBold(True)

        self.table.setRowCount(len(filtered))
        for row, c in enumerate(filtered):
            client_id = c["id"]
            it_id = QTableWidgetItem(f"#{client_id}")
            it_id.setData(Qt.UserRole, client_id)
            it_id.setForeground(fg_main)

            it_name = QTableWidgetItem(c["nombre_completo"])
            it_name.setFont(font_bold)
            it_name.setForeground(fg_main)

            it_tel = QTableWidgetItem(c["telefono"])
            it_tel.setForeground(fg_main)

            it_email = QTableWidgetItem(c["email"])
            it_email.setForeground(fg_main)

            it_alta = QTableWidgetItem(c["fecha_alta"])
            it_alta.setForeground(fg_main)

            it_loans = QTableWidgetItem(c["prestamos_str"])
            it_loans.setForeground(fg_main)

            self.table.setItem(row, 0, it_id)
            self.table.setItem(row, 1, it_name)
            self.table.setItem(row, 2, it_tel)
            self.table.setItem(row, 3, it_email)
            self.table.setItem(row, 4, it_alta)
            self.table.setItem(row, 5, it_loans)

            # Scoring Badge widget in table cell
            badge = ScoringBadge(c["scoring"], parent=self.table)
            self.table.setCellWidget(row, 6, badge)

            # Actions cell with quick Delete and Edit buttons
            actions_widget = QWidget(self.table)
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignCenter)

            btn_row_edit = ToolButton(FluentIcon.EDIT, actions_widget)
            btn_row_edit.setToolTip("Editar cliente")
            btn_row_edit.setFixedSize(28, 28)
            btn_row_edit.clicked.connect(lambda _, cid=client_id: self._edit_client(cid))

            btn_row_del = ToolButton(FluentIcon.DELETE, actions_widget)
            btn_row_del.setToolTip("Eliminar cliente")
            btn_row_del.setFixedSize(28, 28)
            btn_row_del.setStyleSheet("""
                ToolButton:hover {
                    background-color: #FEE2E2;
                }
            """)
            btn_row_del.clicked.connect(lambda _, cid=client_id: self._delete_client(cid))

            actions_layout.addWidget(btn_row_edit)
            actions_layout.addWidget(btn_row_del)
            self.table.setCellWidget(row, 7, actions_widget)

    def _get_selected_client_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        it_id = self.table.item(row, 0)
        return it_id.data(Qt.UserRole) if it_id else None

    def _open_new_client(self):
        dlg = ClientDialog(parent=self)
        dlg.client_saved.connect(self.refresh_clients)
        dlg.exec()

    def _edit_selected_client(self):
        client_id = self._get_selected_client_id()
        if not client_id:
            InfoBar.warning(
                "Seleccionar Cliente",
                "Por favor seleccione un cliente de la tabla para editar.",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        self._edit_client(client_id)

    def _delete_selected_client(self):
        client_id = self._get_selected_client_id()
        if not client_id:
            InfoBar.warning(
                "Seleccionar Cliente",
                "Por favor seleccione el cliente que desea eliminar de la tabla.",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        self._delete_client(client_id)

    def _on_item_double_clicked(self, item):
        row = item.row()
        it_id = self.table.item(row, 0)
        if it_id:
            client_id = it_id.data(Qt.UserRole)
            self._edit_client(client_id)

    def _edit_client(self, client_id: int):
        dlg = ClientDialog(client_id=client_id, parent=self)
        dlg.client_saved.connect(self.refresh_clients)
        dlg.exec()

    def _show_context_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return
        it_id = self.table.item(row, 0)
        if not it_id:
            return
        client_id = it_id.data(Qt.UserRole)

        menu = QMenu(self)
        act_edit = menu.addAction("Editar Datos de Cliente")
        act_del = menu.addAction("Eliminar Cliente")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self._edit_client(client_id)
        elif action == act_del:
            self._delete_client(client_id)

    def _delete_client(self, client_id: int):
        """
        Deletes client with explicit Sí / No confirmation prompt.
        """
        with get_session() as session:
            c = session.get(Cliente, client_id)
            if not c:
                return
            nombre = c.nombre_completo
            cant_prestamos = len(c.prestamos)

        # Modern Fluent MessageBox with explicit Sí and No buttons
        msg_box = MessageBox(
            "Confirmar Eliminación de Cliente",
            f"¿Está seguro de que desea eliminar al cliente {nombre}?\n\n"
            f"⚠️ ADVERTENCIA: Esta acción es definitiva y eliminará también {cant_prestamos} préstamo(s) y todos sus registros de pagos asociados en el sistema.",
            self.window()
        )
        msg_box.yesButton.setText("Sí")
        msg_box.cancelButton.setText("No")

        if msg_box.exec():
            with get_session() as session:
                c = session.get(Cliente, client_id)
                if c:
                    session.delete(c)

            self.refresh_clients()
            self.client_deleted.emit(client_id)
            InfoBar.success(
                "Cliente Eliminado",
                f"El cliente {nombre} y sus registros fueron eliminados correctamente.",
                parent=self,
                position=InfoBarPosition.TOP
            )
