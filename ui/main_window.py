from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon, setTheme, Theme,
    setThemeColor
)
from config import APP_TITLE, APP_VERSION, BASE_DIR
from ui.views.dashboard_view import DashboardView
from ui.views.new_loan_view import NewLoanView
from ui.views.clients_view import ClientsView
from ui.views.cash_view import CashView
from ui.views.settings_view import SettingsView


class MainWindow(MSFluentWindow):
    """
    Main Application Window implementing Windows Fluent 11 design
    with NavigationInterface sidebar.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{APP_VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(960, 600)

        # Set window icon
        icon_path = BASE_DIR / "resources" / "app_icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(max(0, x), max(0, y))

        self._init_sub_interfaces()
        self._connect_signals()

    def _init_sub_interfaces(self):
        # 1. Dashboard View
        self.dashboard_view = DashboardView(self)
        self.dashboard_view.setObjectName("dashboardInterface")
        self.addSubInterface(self.dashboard_view, FluentIcon.HOME, "Dashboard")

        # 2. New Loan View
        self.new_loan_view = NewLoanView(self)
        self.new_loan_view.setObjectName("newLoanInterface")
        self.addSubInterface(self.new_loan_view, FluentIcon.ADD, "Nuevo Préstamo")

        # 3. Clients View
        self.clients_view = ClientsView(self)
        self.clients_view.setObjectName("clientsInterface")
        self.addSubInterface(self.clients_view, FluentIcon.PEOPLE, "Clientes")

        # 4. Cash Balances & Arqueos View
        self.cash_view = CashView(self)
        self.cash_view.setObjectName("cashInterface")
        self.addSubInterface(self.cash_view, FluentIcon.BOOK_SHELF, "Balances / Arqueos")

        # 5. Settings & Backups View (Bottom position)
        self.settings_view = SettingsView(self)
        self.settings_view.setObjectName("settingsInterface")
        self.addSubInterface(
            self.settings_view,
            FluentIcon.SETTING,
            "Ajustes y Backup",
            position=NavigationItemPosition.BOTTOM
        )

    def _connect_signals(self):
        # When user clicks "Nuevo Préstamo" from Dashboard
        self.dashboard_view.request_new_loan.connect(self._go_to_new_loan)

        # When a loan is edited, deleted, or paid from dashboard, update cash balances
        self.dashboard_view.loan_changed.connect(self._on_loan_changed)

        # When a loan is successfully created, refresh and return to Dashboard
        self.new_loan_view.loan_created.connect(self._on_loan_created)

        # When a client is deleted, synchronize dashboard, loan view and cash balances
        self.clients_view.client_deleted.connect(self._on_client_deleted)

        # When a daily closure or cash configuration changes, update dashboard
        self.cash_view.balance_updated.connect(self.dashboard_view.refresh_dashboard)

    def _go_to_new_loan(self):
        self.new_loan_view.reload_clients()
        self.switchTo(self.new_loan_view)

    def _on_loan_created(self, prestamo_id: int):
        self.dashboard_view.refresh_dashboard()
        self.cash_view.refresh_all()
        self.switchTo(self.dashboard_view)

    def _on_loan_changed(self):
        self.cash_view.refresh_all()

    def _on_client_deleted(self, client_id: int):
        self.dashboard_view.refresh_dashboard()
        self.cash_view.refresh_all()
        self.new_loan_view.reload_clients()
