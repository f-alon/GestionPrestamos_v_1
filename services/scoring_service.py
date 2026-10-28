from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from services.financial_service import calcular_prestamo, parse_date


@dataclass
class ScoringResult:
    nivel: str               # 'ROJO', 'VERDE', 'NEUTRO', 'AMARILLO'
    titulo: str              # Titulo corto para badge
    mensaje: str             # Explicación detallada
    prestamos_totales: int
    prestamos_activos: int
    prestamos_cerrados: int
    cerrados_con_mora: int
    tiene_mora_activa: bool
    color_hex: str           # Hex color for UI styling
    bg_hex: str              # Light background color for UI badge/banner


def evaluar_cliente(cliente) -> ScoringResult:
    """
    Evaluates customer credit scoring according to specifications:
    1. ALERTA ROJA (Cliente Moroso / Riesgo Alto):
       - Condicion: Tiene un prestamo activo con dias_atraso > 0, o mas del 20% de sus prestamos cerrados registraron atraso.
       - UI: "Atención: El cliente registra antecedentes de mora."
    2. BADGE VERDE (Cliente Cumplidor / Confiable):
       - Condicion: Al menos 1 prestamo previo finalizado y 0 dias de mora acumulados.
       - UI: "Cliente Cumplidor (Sin atrasos)"
    3. BADGE NEUTRO (Sin Historial):
       - Condicion: Cliente nuevo sin prestamos anteriores.
    """
    prestamos = list(getattr(cliente, "prestamos", []))

    if not prestamos:
        return ScoringResult(
            nivel="NEUTRO",
            titulo="Sin Historial",
            mensaje="Cliente nuevo sin registros crediticios previos.",
            prestamos_totales=0,
            prestamos_activos=0,
            prestamos_cerrados=0,
            cerrados_con_mora=0,
            tiene_mora_activa=False,
            color_hex="#6C757D",
            bg_hex="#E9ECEF"
        )

    prestamos_activos = [p for p in prestamos if p.estado == "EN_CURSO"]
    prestamos_cerrados = [p for p in prestamos if p.estado == "TERMINADO"]

    # Evaluar morosidad en préstamos activos
    tiene_mora_activa = False
    for p in prestamos_activos:
        res = calcular_prestamo(p)
        if res.dias_atraso > 0:
            tiene_mora_activa = True
            break

    # Evaluar morosidad histórica en préstamos cerrados
    cerrados_con_mora = 0
    for p in prestamos_cerrados:
        fecha_fin = parse_date(p.fecha_fin)
        # Check payments dates
        pagos = list(getattr(p, "pagos", []))
        registro_mora = False
        if pagos:
            for pago in pagos:
                f_pago = parse_date(pago.fecha_pago)
                if f_pago > fecha_fin:
                    registro_mora = True
                    break
        else:
            # Loan was terminated without recorded payments or default
            registro_mora = False

        if registro_mora:
            cerrados_con_mora += 1

    total_cerrados = len(prestamos_cerrados)
    pct_cerrados_mora = (cerrados_con_mora / total_cerrados) if total_cerrados > 0 else 0.0

    # 1. Alerta Roja
    if tiene_mora_activa or (total_cerrados > 0 and pct_cerrados_mora > 0.20):
        motivos = []
        if tiene_mora_activa:
            motivos.append("posee préstamo activo con días de atraso")
        if total_cerrados > 0 and pct_cerrados_mora > 0.20:
            motivos.append(f"{round(pct_cerrados_mora * 100, 1)}% de sus préstamos cerrados registraron atraso")

        return ScoringResult(
            nivel="ROJO",
            titulo="Riesgo Alto / Moroso",
            mensaje=f"Atención: El cliente registra antecedentes de mora ({', '.join(motivos)}).",
            prestamos_totales=len(prestamos),
            prestamos_activos=len(prestamos_activos),
            prestamos_cerrados=total_cerrados,
            cerrados_con_mora=cerrados_con_mora,
            tiene_mora_activa=tiene_mora_activa,
            color_hex="#DC3545",
            bg_hex="#F8D7DA"
        )

    # 2. Badge Verde
    if total_cerrados >= 1 and cerrados_con_mora == 0 and not tiene_mora_activa:
        return ScoringResult(
            nivel="VERDE",
            titulo="Cliente Cumplidor",
            mensaje="Cliente Cumplidor (Sin atrasos). Historial 100% positivo.",
            prestamos_totales=len(prestamos),
            prestamos_activos=len(prestamos_activos),
            prestamos_cerrados=total_cerrados,
            cerrados_con_mora=0,
            tiene_mora_activa=False,
            color_hex="#198754",
            bg_hex="#D1E7DD"
        )

    # 3. Préstamos en curso sin atraso ni historial previo cerrado
    return ScoringResult(
        nivel="NEUTRO",
        titulo="En Curso / Regular",
        mensaje="Cliente con operaciones al día sin antecedentes negativos.",
        prestamos_totales=len(prestamos),
        prestamos_activos=len(prestamos_activos),
        prestamos_cerrados=total_cerrados,
        cerrados_con_mora=cerrados_con_mora,
        tiene_mora_activa=False,
        color_hex="#0D6EFD",
        bg_hex="#CFE2FF"
    )

