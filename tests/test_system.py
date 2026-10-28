import os
import unittest
from datetime import date, timedelta
from database import init_db, get_session, Cliente, Prestamo, Pago
from services.financial_service import (
    calcular_prestamo, simular_prestamo, calcular_fecha_fin, FinancialSummary
)
from services.scoring_service import evaluar_cliente
from services.notification_service import (
    limpiar_telefono, generar_link_whatsapp, redactar_mensaje_cobro, redactar_comprobante_pago
)
from services.export_service import backup_database, export_prestamos_csv, export_prestamos_excel


class TestGestionPrestamos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_financial_calculations(self):
        # Loan with 10,000, 20% interest, 30 days
        sim = simular_prestamo(10000.0, 20.0, "DIAS", 30)
        self.assertEqual(sim["total_base"], 12000.0)
        self.assertEqual(sim["interes_monto"], 2000.0)

        # Mock loan without mora
        class MockPrestamo:
            monto_prestado = 10000.0
            porcentaje_interes = 20.0
            tasa_mora_diaria = 1.0
            estado = "EN_CURSO"
            fecha_fin = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
            pagos = []

        calc = calcular_prestamo(MockPrestamo())
        self.assertEqual(calc.total_base, 12000.0)
        self.assertEqual(calc.dias_atraso, 0)
        self.assertEqual(calc.mora_acumulada, 0.0)
        self.assertEqual(calc.saldo_restante, 12000.0)
        self.assertFalse(calc.esta_vencido)

    def test_02_mora_calculations(self):
        # Mock loan overdue by 5 days, 1% per day
        # total_base = 10,000 * 1.20 = 12,000
        # pago = 2,000 -> saldo_base_pendiente = 10,000
        # mora = 10,000 * (1.0 / 100) * 5 = 500
        # saldo_restante = (12,000 + 500) - 2,000 = 10,500
        class MockPago:
            monto = 2000.0

        class MockPrestamoMora:
            monto_prestado = 10000.0
            porcentaje_interes = 20.0
            tasa_mora_diaria = 1.0
            estado = "EN_CURSO"
            fecha_fin = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
            pagos = [MockPago()]

        calc = calcular_prestamo(MockPrestamoMora())
        self.assertEqual(calc.dias_atraso, 5)
        self.assertEqual(calc.saldo_base_pendiente, 10000.0)
        self.assertEqual(calc.mora_acumulada, 500.0)
        self.assertEqual(calc.total_abonado, 2000.0)
        self.assertEqual(calc.saldo_restante, 10500.0)
        self.assertTrue(calc.esta_vencido)
        self.assertFalse(calc.puede_cerrar)

    def test_03_credit_scoring(self):
        # 1. New Client -> NEUTRO
        class MockClienteNuevo:
            prestamos = []

        res_nuevo = evaluar_cliente(MockClienteNuevo())
        self.assertEqual(res_nuevo.nivel, "NEUTRO")
        self.assertEqual(res_nuevo.titulo, "Sin Historial")

        # 2. Compliant Client -> VERDE
        class MockPagoC1:
            fecha_pago = "2026-01-10 10:00:00"

        class MockPrestamoC1:
            estado = "TERMINADO"
            fecha_fin = "2026-01-15"
            pagos = [MockPagoC1()]
            monto_prestado = 1000.0
            porcentaje_interes = 10.0
            tasa_mora_diaria = 1.0

        class MockClienteCumplidor:
            prestamos = [MockPrestamoC1()]

        res_cumplidor = evaluar_cliente(MockClienteCumplidor())
        self.assertEqual(res_cumplidor.nivel, "VERDE")
        self.assertIn("Cumplidor", res_cumplidor.titulo)

        # 3. Moroso Client -> ROJO
        class MockPrestamoMoroso:
            estado = "EN_CURSO"
            fecha_fin = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
            pagos = []
            monto_prestado = 1000.0
            porcentaje_interes = 10.0
            tasa_mora_diaria = 1.0

        class MockClienteMoroso:
            prestamos = [MockPrestamoMoroso()]

        res_moroso = evaluar_cliente(MockClienteMoroso())
        self.assertEqual(res_moroso.nivel, "ROJO")
        self.assertTrue(res_moroso.tiene_mora_activa)

    def test_04_notifications_whatsapp(self):
        tel = "+54 9 11 1234-5678"
        clean = limpiar_telefono(tel)
        self.assertEqual(clean, "5491112345678")

        url = generar_link_whatsapp(tel, "Mensaje de prueba")
        self.assertTrue(url.startswith("https://wa.me/5491112345678?text="))
        self.assertIn("Mensaje", url)

    def test_05_backup_and_exports(self):
        ok, res = backup_database()
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(res))

        with get_session() as session:
            prestamos = session.query(Prestamo).all()
            csv_path = os.path.join(os.path.dirname(res), "test_export.csv")
            ok_csv, _ = export_prestamos_csv(prestamos, csv_path)
            self.assertTrue(ok_csv)
            self.assertTrue(os.path.exists(csv_path))

            xlsx_path = os.path.join(os.path.dirname(res), "test_export.xlsx")
            ok_xlsx, _ = export_prestamos_excel(prestamos, xlsx_path)
            self.assertTrue(ok_xlsx)
            self.assertTrue(os.path.exists(xlsx_path))


if __name__ == "__main__":
    unittest.main()

