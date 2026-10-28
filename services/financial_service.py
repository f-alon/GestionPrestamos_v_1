from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Union
from config import DATE_FORMAT


@dataclass
class FinancialSummary:
    monto_prestado: float
    porcentaje_interes: float
    interes_monto: float
    total_base: float
    dias_atraso: int
    tasa_mora_diaria: float
    saldo_base_pendiente: float
    mora_acumulada: float
    total_abonado: float
    total_a_pagar: float
    saldo_restante: float
    esta_vencido: bool
    puede_cerrar: bool
    estado: str


def parse_date(d: Union[str, date, datetime]) -> date:
    """Parses various date representations into a standard date object."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        # Handle 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
        clean = d.strip().split(" ")[0]
        return datetime.strptime(clean, DATE_FORMAT).date()
    raise ValueError(f"No se pudo parsear la fecha: {d}")


def calcular_fecha_fin(fecha_inicio: Union[str, date], tipo_plazo: str, duracion: int) -> date:
    """Calculates due date based on term type and duration."""
    f_ini = parse_date(fecha_inicio)
    if tipo_plazo.upper() == "SEMANAS":
        return f_ini + timedelta(days=duracion * 7)
    # Default to DIAS
    return f_ini + timedelta(days=duracion)


def calcular_prestamo(prestamo, fecha_referencia: Optional[date] = None) -> FinancialSummary:
    """
    Computes all financial metrics for a loan entity according to the business specifications:
    - total_base = monto_prestado * (1.0 + (porcentaje_interes / 100.0))
    - dias_diferencia = (hoy - fecha_fin).days
    - if estado == 'EN_CURSO' and dias_diferencia > 0: dias_atraso = dias_diferencia else 0
    - saldo_base_pendiente = max(0.0, total_base - total_abonado)
    - mora_acumulada = saldo_base_pendiente * (tasa_mora_diaria / 100.0) * dias_atraso
    - saldo_restante = (total_base + mora_acumulada) - total_abonado
    """
    hoy = fecha_referencia or date.today()
    fecha_fin = parse_date(prestamo.fecha_fin)
    dias_diferencia = (hoy - fecha_fin).days

    monto_prestado = float(prestamo.monto_prestado)
    porcentaje_interes = float(prestamo.porcentaje_interes)
    tasa_mora_diaria = float(prestamo.tasa_mora_diaria)
    estado = getattr(prestamo, "estado", "EN_CURSO")

    # A. Total Base a Devolver
    total_base = round(monto_prestado * (1.0 + (porcentaje_interes / 100.0)), 2)
    interes_monto = round(total_base - monto_prestado, 2)

    # B. Calculo de Dias de Atraso
    if estado == "EN_CURSO" and dias_diferencia > 0:
        dias_atraso = dias_diferencia
    else:
        dias_atraso = 0

    # D. Pagos efectuados
    pagos = getattr(prestamo, "pagos", [])
    total_abonado = round(sum(float(p.monto) for p in pagos), 2)

    # Saldo base pendiente para cálculo punitorio
    saldo_base_pendiente = max(0.0, round(total_base - total_abonado, 2))

    # C. Interes Punitorio por Mora
    if estado == "EN_CURSO" and dias_atraso > 0 and saldo_base_pendiente > 0:
        mora_acumulada = round(saldo_base_pendiente * (tasa_mora_diaria / 100.0) * dias_atraso, 2)
    else:
        mora_acumulada = 0.0

    total_a_pagar = round(total_base + mora_acumulada, 2)
    saldo_restante = round(total_a_pagar - total_abonado, 2)
    if saldo_restante < 0:
        saldo_restante = 0.0

    esta_vencido = (estado == "EN_CURSO" and dias_diferencia > 0)
    puede_cerrar = (saldo_restante <= 0.01)

    return FinancialSummary(
        monto_prestado=monto_prestado,
        porcentaje_interes=porcentaje_interes,
        interes_monto=interes_monto,
        total_base=total_base,
        dias_atraso=dias_atraso,
        tasa_mora_diaria=tasa_mora_diaria,
        saldo_base_pendiente=saldo_base_pendiente,
        mora_acumulada=mora_acumulada,
        total_abonado=total_abonado,
        total_a_pagar=total_a_pagar,
        saldo_restante=saldo_restante,
        esta_vencido=esta_vencido,
        puede_cerrar=puede_cerrar,
        estado=estado
    )


def simular_prestamo(monto: float, interes_pct: float, tipo_plazo: str, duracion: int, fecha_inicio: Optional[date] = None):
    """Calculates projection for a new loan simulation before persisting."""
    f_ini = fecha_inicio or date.today()
    f_fin = calcular_fecha_fin(f_ini, tipo_plazo, duracion)
    total_base = round(monto * (1.0 + (interes_pct / 100.0)), 2)
    interes_monto = round(total_base - monto, 2)

    return {
        "monto_prestado": monto,
        "porcentaje_interes": interes_pct,
        "interes_monto": interes_monto,
        "total_base": total_base,
        "fecha_inicio": f_ini,
        "fecha_fin": f_fin,
        "tipo_plazo": tipo_plazo,
        "duracion_plazo": duracion
    }

