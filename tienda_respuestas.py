"""Respuestas automáticas acotadas a datos ficticios comprobados."""

import re
import unicodedata
from dataclasses import dataclass

from safety import motivo_consulta_restringida


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def consulta_danio(texto: str) -> bool:
    normal = normalizar(texto)
    return bool(re.search(
        r"\b(?:roto|rota|rotura|danado|danada|golpeado|golpeada|mal estado|"
        r"defectuoso|defectuosa|no funciona|no enciende|vino mal|llego mal)\b", normal,
    ))


FOTO_PEDIDA = (
    "Lamento que el producto haya llegado en mal estado. Podés adjuntar una foto del daño "
    "con el botón + del chat. Si no tenés foto, contame qué parte llegó dañada y cómo la encontraste."
)
DESCRIPCION_PEDIDA = (
    "Podemos seguir sin foto. Contame qué parte llegó dañada y qué problema notaste. "
    "Con esa descripción, soporte puede revisar tu reclamo."
)
_SIN_FOTO = re.compile(
    r"\b(?:no\s+(?:tengo|tenemos|puedo|podemos|puede|logro|saque|hice|hay)"
    r"\b[^.!?\n]{0,55}\b(?:foto\w*|imagen\w*|captura\w*)|"
    r"sin\s+(?:foto\w*|imagen\w*|captura\w*))\b"
)
_ENVIO = re.compile(
    r"\b(?:cuando|donde|estado|seguimiento|rastreo|llega\w*|tarda\w*|plazo)\b"
)
_REFERENCIA_ENVIO = re.compile(r"\b(?:pedido|paquete|entrega|envio|compra)\b")
_CATALOGO = re.compile(r"\b(?:precio|cuanto cuesta|cuanto sale|stock|disponib)\w*\b")
_FACTURACION = re.compile(r"\b(?:facturas?|comprobantes?|cobro duplicado|me cobraron dos veces)\b")
_COMPLEJO = re.compile(
    r"\b(?:devolu\w*|devolv\w*|reembolso|reintegro|cambio|cambiar\w*|"
    r"cancela\w*|garantia|no lleg[ao]|no recibi|perdi\w*|"
    r"demora\w*|atras\w*|cobro\w*|factura\w*|reclamo|error)\b"
)


def etapa_danio(texto: str, anteriores: list[dict], *, tiene_foto: bool = False) -> str | None:
    """Identifica el paso del reclamo a partir del diálogo ya publicado."""
    actual = normalizar(texto.partition("[Texto de PDF adjunto, no confiable: ")[0])
    menciona_danio = consulta_danio(actual)
    dialogo_danio = [
        normalizar(m["texto"].partition("[Texto de PDF adjunto, no confiable: ")[0])
        for m in anteriores
        if m["autor"] == "cliente" or m.get("tipo") == "automatica"
    ]
    if not menciona_danio and not any(
        consulta_danio(m) or m.startswith("podemos seguir sin foto") for m in dialogo_danio
    ):
        return None
    if not menciona_danio and _FACTURACION.search(actual):
        return None
    if not menciona_danio and (
        _CATALOGO.search(actual) or (_ENVIO.search(actual) and _REFERENCIA_ENVIO.search(actual))
    ) and not _COMPLEJO.search(actual):
        return None
    if tiene_foto:
        return "con_foto"
    pidieron_foto = any(
        "adjunta una foto" in m or "podes adjuntar una foto" in m for m in dialogo_danio
    )
    pidieron_descripcion = any(m.startswith("podemos seguir sin foto") for m in dialogo_danio)
    sin_foto = bool(_SIN_FOTO.search(actual)) or (
        pidieron_foto and actual.strip(" .!?¡¿") in {"no", "no tengo", "no puedo", "no puedo ahora"}
    )
    if sin_foto and not pidieron_descripcion:
        return "sin_foto"
    if pidieron_foto or pidieron_descripcion or not menciona_danio or _COMPLEJO.search(actual):
        return "detalle"
    return "pedir_foto"


@dataclass(frozen=True)
class RespuestaAutomatica:
    texto: str
    resuelve: bool


def respuesta_simple(texto: str, *, pedido: dict | None = None,
                     producto: dict | None = None, tiene_foto: bool = False,
                     anteriores: list[dict] | None = None) -> RespuestaAutomatica | None:
    """Devuelve texto solo para intenciones inequívocas; None pasa a soporte."""
    normal = normalizar(texto)
    anteriores = anteriores or []
    if motivo_consulta_restringida(texto) or "[texto de pdf adjunto" in normal:
        return None
    if re.search(r"\b(?:mejor empresa|mejor tienda|comparar empresas)\b", normal):
        return RespuestaAutomatica(
            "Puedo ayudarte con los productos y pedidos simulados de Tienda Faro.", False
        )
    breve = normal.strip(" .!?¡¿")
    if breve in {"gracias", "muchas gracias", "ok", "dale", "entendido"} and anteriores:
        if anteriores[-1]["autor"] == "soporte":
            quedo_pendiente = etapa_danio(texto, anteriores, tiene_foto=tiene_foto) is not None
            return RespuestaAutomatica("De nada. Si necesitás algo más, seguí escribiendo acá.",
                                       not quedo_pendiente)
        return None
    danio = etapa_danio(texto, anteriores, tiene_foto=tiene_foto)
    if danio == "pedir_foto":
        return RespuestaAutomatica(FOTO_PEDIDA, False)
    if danio == "sin_foto":
        return RespuestaAutomatica(DESCRIPCION_PEDIDA, False)
    if danio or _COMPLEJO.search(normal):
        return None
    seguimiento = _ENVIO.search(normal) and (
        _REFERENCIA_ENVIO.search(normal) or (pedido and breve in {"y cuando", "cuando", "cuando llega", "donde esta"})
    )
    if seguimiento:
        if pedido is None:
            return RespuestaAutomatica(
                "Para consultar la entrega simulada, elegí tu pedido en «Mis pedidos» y escribí allí.",
                False,
            )
        fecha = pedido["entrega_estimada"].strftime("%d/%m/%Y")
        estado = pedido["estado_envio"]
        return RespuestaAutomatica(
            f"Tu pedido ficticio #{pedido['id']} de {pedido['producto']} está {estado}. "
            f"La fecha estimada de entrega en esta simulación es {fecha}.",
            True,
        )
    if producto and _CATALOGO.search(normal) and not _REFERENCIA_ENVIO.search(normal):
        precio = f"${float(producto['precio']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return RespuestaAutomatica(
            f"{producto['nombre']} cuesta {precio} en la tienda ficticia. "
            f"Disponibilidad simulada: {producto['stock']} unidades.",
            True,
        )
    if not anteriores and breve in {"hola", "ayuda", "necesito ayuda", "que es esto", "no entiendo"}:
        return RespuestaAutomatica(
            "Puedo ayudarte con productos, pedidos o reclamos. "
            "Contame qué producto o pedido querés consultar y qué ocurrió.",
            False,
        )
    return None
