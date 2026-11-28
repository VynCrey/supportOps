"""Respuestas automáticas acotadas a datos ficticios comprobados."""

import re
import unicodedata

from safety import motivo_consulta_restringida


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def consulta_danio(texto: str) -> bool:
    normal = normalizar(texto)
    return bool(re.search(
        r"\b(?:roto|rota|rotura|danado|danada|golpeado|golpeada|mal estado|"
        r"defectuoso|defectuosa|no funciona|vino mal|llego mal)\b", normal,
    ))


def respuesta_simple(texto: str, *, pedido: dict | None = None,
                     producto: dict | None = None, tiene_foto: bool = False) -> str | None:
    """Devuelve texto solo para intenciones inequívocas; None pasa a soporte."""
    normal = normalizar(texto)
    if motivo_consulta_restringida(texto) or "[texto de pdf adjunto" in normal:
        return None
    if re.search(r"\b(?:mejor empresa|mejor tienda|comparar empresas)\b", normal):
        return ("Esta demostración solo tiene información de Tienda Faro ficticia. "
                "Puedo ayudarte con sus productos y pedidos simulados, sin comparar empresas reales.")
    if consulta_danio(texto):
        if tiene_foto:
            return None
        return (
            "Lamento que el producto haya llegado en mal estado. "
            "Adjuntá una foto en esta conversación para que soporte pueda revisar "
            "el daño. No compartas datos de pago ni contraseñas."
        )
    if re.search(r"\b(?:cuando|donde|llega|llegara|entrega|envio|seguimiento|estado)\b", normal):
        if re.search(r"\b(?:devolucion|reembolso|roto|reclamo|error|no lleg[ao]|"
                     r"no recibi|perdido|demora|atraso)\b", normal):
            return None
        if pedido is None:
            return "Para consultar la entrega simulada, elegí tu pedido en «Mis pedidos» y escribí allí."
        fecha = pedido["entrega_estimada"].strftime("%d/%m/%Y")
        estado = pedido["estado_envio"]
        return (
            f"Tu pedido ficticio #{pedido['id']} de {pedido['producto']} está {estado}. "
            f"La fecha estimada de entrega en esta simulación es {fecha}. "
            "No corresponde a un envío real."
        )
    if producto and re.search(r"\b(?:precio|cuanto cuesta|cuanto sale|stock|disponib)\w*\b", normal):
        if re.search(r"\b(?:pedido|cobro|factura|devolucion|reclamo)\b", normal):
            return None
        precio = f"${float(producto['precio']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return (
            f"{producto['nombre']} cuesta {precio} en la tienda ficticia. "
            f"Disponibilidad simulada: {producto['stock']} unidades."
        )
    if normal.strip(" .!?¡¿") in {"hola", "ayuda", "necesito ayuda", "que es esto", "no entiendo"}:
        return ("Puedo ayudarte con productos, pedidos o reclamos de Tienda Faro ficticia. "
                "Contame qué producto o pedido querés consultar y qué ocurrió.")
    return None
