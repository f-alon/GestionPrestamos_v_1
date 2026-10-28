from datetime import date, datetime, timedelta
from database.connection import get_session
from database.models import Cliente, Prestamo, Pago
from config import DATE_FORMAT, DATETIME_FORMAT


def seed_demo_data_if_empty():
    """Populates demo clients and loans if database is empty."""
    with get_session() as session:
        if session.query(Cliente).count() > 0:
            return  # Already has data

        hoy = date.today()

        # 1. Client 1: Cliente Cumplidor
        c1 = Cliente(
            nombre="Lucas",
            apellido="Martínez",
            telefono="5491140001111",
            email="lucas.martinez@ejemplo.com",
            notas="Cliente confiable. Siempre abona en término.",
            fecha_alta=(datetime.now() - timedelta(days=90)).strftime(DATETIME_FORMAT)
        )
        session.add(c1)
        session.flush()

        # Préstamo 1 cerrado con éxito sin mora
        p1 = Prestamo(
            cliente_id=c1.id,
            monto_prestado=50000.0,
            porcentaje_interes=20.0,
            tipo_plazo="DIAS",
            duracion_plazo=30,
            fecha_inicio=(hoy - timedelta(days=70)).strftime(DATE_FORMAT),
            fecha_fin=(hoy - timedelta(days=40)).strftime(DATE_FORMAT),
            tasa_mora_diaria=1.0,
            estado="TERMINADO"
        )
        session.add(p1)
        session.flush()

        # Pago total de p1 realizado a tiempo
        pago_p1 = Pago(
            prestamo_id=p1.id,
            monto=60000.0,
            fecha_pago=(hoy - timedelta(days=42)).strftime(DATETIME_FORMAT),
            metodo_pago="Transferencia Bancaria",
            comprobante_ref="TRF-884912"
        )
        session.add(pago_p1)

        # Préstamo 2 activo y al día
        p2 = Prestamo(
            cliente_id=c1.id,
            monto_prestado=80000.0,
            porcentaje_interes=25.0,
            tipo_plazo="DIAS",
            duracion_plazo=45,
            fecha_inicio=(hoy - timedelta(days=10)).strftime(DATE_FORMAT),
            fecha_fin=(hoy + timedelta(days=35)).strftime(DATE_FORMAT),
            tasa_mora_diaria=1.0,
            estado="EN_CURSO"
        )
        session.add(p2)
        session.flush()

        pago_p2 = Pago(
            prestamo_id=p2.id,
            monto=30000.0,
            fecha_pago=(hoy - timedelta(days=2)).strftime(DATETIME_FORMAT),
            metodo_pago="Efectivo",
            comprobante_ref="REC-001"
        )
        session.add(pago_p2)

        # 2. Client 2: Cliente Moroso (Alerta Roja)
        c2 = Cliente(
            nombre="Gonzalo",
            apellido="Fernández",
            telefono="5491155552222",
            email="gonzalo.f@ejemplo.com",
            notas="Registra atrasos en los pagos. Llamar antes de prestar.",
            fecha_alta=(datetime.now() - timedelta(days=60)).strftime(DATETIME_FORMAT)
        )
        session.add(c2)
        session.flush()

        # Préstamo activo vencido hace 7 días (Mora acumulada)
        p3 = Prestamo(
            cliente_id=c2.id,
            monto_prestado=40000.0,
            porcentaje_interes=20.0,
            tipo_plazo="DIAS",
            duracion_plazo=20,
            fecha_inicio=(hoy - timedelta(days=27)).strftime(DATE_FORMAT),
            fecha_fin=(hoy - timedelta(days=7)).strftime(DATE_FORMAT),
            tasa_mora_diaria=1.0,  # 1% diario
            estado="EN_CURSO"
        )
        session.add(p3)
        session.flush()

        pago_p3 = Pago(
            prestamo_id=p3.id,
            monto=15000.0,
            fecha_pago=(hoy - timedelta(days=15)).strftime(DATETIME_FORMAT),
            metodo_pago="Mercado Pago",
            comprobante_ref="MP-991283"
        )
        session.add(pago_p3)

        # 3. Client 3: Nuevo Cliente (Badge Neutro)
        c3 = Cliente(
            nombre="Sofía",
            apellido="Albarracín",
            telefono="5491177773333",
            email="sofia.albarracin@ejemplo.com",
            notas="Cliente recién registrada, solicita información para primer crédito.",
            fecha_alta=datetime.now().strftime(DATETIME_FORMAT)
        )
        session.add(c3)

