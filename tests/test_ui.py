import os
import sys
import unittest

# Run Qt offscreen without requiring a physical monitor or display
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.dialogs.client_dialog import ClientDialog
from ui.dialogs.payment_dialog import PaymentDialog
from ui.dialogs.loan_detail_dialog import LoanDetailDialog
from database import init_db, get_session, Prestamo, Cliente
from database.seed import seed_demo_data_if_empty


class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data_if_empty()
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_01_main_window_instantiation(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertIsNotNone(window.dashboard_view)
        self.assertIsNotNone(window.new_loan_view)
        self.assertIsNotNone(window.clients_view)
        self.assertIsNotNone(window.settings_view)

        # Verify Dashboard table has rows from seed
        self.assertGreater(window.dashboard_view.table.rowCount(), 0)

        # Verify Clients table has rows from seed
        self.assertGreater(window.clients_view.table.rowCount(), 0)

        window.close()

    def test_02_dialogs_instantiation(self):
        # ClientDialog
        dlg_client = ClientDialog()
        self.assertIsNotNone(dlg_client)
        dlg_client.close()

        # Find existing loan for Payment & Detail dialogs
        with get_session() as session:
            p = session.query(Prestamo).first()
            self.assertIsNotNone(p)
            p_id = p.id

        dlg_pago = PaymentDialog(p_id)
        self.assertIsNotNone(dlg_pago)
        dlg_pago.close()

        dlg_detail = LoanDetailDialog(p_id)
        self.assertIsNotNone(dlg_detail)
        dlg_detail.close()


if __name__ == "__main__":
    unittest.main()

