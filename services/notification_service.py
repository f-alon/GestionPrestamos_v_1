import re
import urllib.parse
import webbrowser
from config import CURRENCY_SYMBOL
from services.financial_service import calcular_prestamo


def limpiar_telefono(telefono: str) -> str:
    """Removes non-digit characters to ensure international WhatsApp format (e.g. 54911xxxxxxxx)."""
    return re.sub(r"[^\d]", "", str(telefono or ""))


def generar_link_whatsapp(telefono: str, mensaje: str) -> str:
    """Creates a wa.me URL with url-encoded message."""
    tel_limpio = limpiar_telefono(telefono)
    mensaje_encoded = urllib.parse.quote(mensaje)
    return f"https://wa.me/{tel_limpio}?text={mensaje_encoded}"


def abrir_whatsapp(telefono: str, mensaje: str) -> bool:
    """Opens browser with WhatsApp link."""
    url = generar_link_whatsapp(telefono, mensaje)
    return webbrowser.open(url)


def redactar_mensaje_cobro(cliente, prestamo) -> str:
    """Generates standard collection or reminder message based on current loan state."""
    res = calcular_prestamo(prestamo)
    nombre = cliente.nombre.strip()

    if res.dias_atraso > 0:
        # Mensaje de mora
        msg = (
            f"Hola {nombre}, te contactamos de Administración sobre tu préstamo #{prestamo.id}.\n"
            f"Te informamos que tu cuota venció el {prestamo.fecha_fin} y registra {res.dias_atraso} días de atraso.\n"
            f"• Saldo base pendiente: {CURRENCY_SYMBOL}{res.saldo_base_pendiente:,.2f}\n"
            f"• Interés por mora ({res.tasa_mora_diaria}% diario): {CURRENCY_SYMBOL}{res.mora_acumulada:,.2f}\n"
            f"• Total a abonar hoy: {CURRENCY_SYMBOL}{res.saldo_restante:,.2f}\n\n"
            f"Por favor, regulariza tu situación a la brevedad para evitar recargos adicionales."
        )
    else:
        # Mensaje recordatorio al día
        msg = (
            f"Hola {nombre}, te contactamos de Administración sobre tu préstamo #{prestamo.id}.\n"
            f"Te recordamos que la fecha de vencimiento es el {prestamo.fecha_fin}.\n"
            f"• Saldo restante: {CURRENCY_SYMBOL}{res.saldo_restante:,.2f}\n"
            f"• Total abonado hasta la fecha: {CURRENCY_SYMBOL}{res.total_abonado:,.2f}\n\n"
            f"¡Muchas gracias por tu compromiso!"
        )

    return msg


def redactar_comprobante_pago(cliente, prestamo, pago) -> str:
    """Generates confirmation message after payment has been recorded."""
    res = calcular_prestamo(prestamo)
    nombre = cliente.nombre.strip()

    msg = (
        f"Hola {nombre}, confirmamos la recepción de tu pago.\n"
        f"• Préstamo #{prestamo.id}\n"
        f"• Monto recibido: {CURRENCY_SYMBOL}{pago.monto:,.2f}\n"
        f"• Fecha: {pago.fecha_pago}\n"
        f"• Medio: {pago.metodo_pago or 'Efectivo'}\n"
    )
    if pago.comprobante_ref:
        msg += f"• Referencia: {pago.comprobante_ref}\n"

    if res.saldo_restante <= 0.01:
        msg += f"\n🎉 ¡Felicitaciones! Tu préstamo ha quedado totalmente cancelado. ¡Gracias por cumplir!"
    else:
        msg += f"\n• Saldo restante actual: {CURRENCY_SYMBOL}{res.saldo_restante:,.2f}\n• Vencimiento: {prestamo.fecha_fin}"

    return msg

