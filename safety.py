import re
import unicodedata


SECRETOS = re.compile(
    r"\b(?:token(?:s)?|contrasena(?:s)?|password|claves?|"
    r"api[ _-]?key|secretos?|otp|codigo(?:s)? de (?:verificacion|"
    r"autenticacion|seguridad)|2fa)\b"
)
PEDIDOS = re.compile(
    r"\b(?:envia\w*|manda\w*|comparte\w*|proporciona\w*|"
    r"facilita\w*|indica\w*|dime|muestra\w*|copia\w*|pega\w*|"
    r"pasa\w*|necesit\w*|solicit\w*)\b"
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in texto if not unicodedata.combining(letra))


def pide_credenciales(borrador: dict, faltantes: list[str] | None = None) -> bool:
    """Detecta pedidos de secretos en preguntas, faltantes o texto propuesto."""
    preguntas = borrador.get("preguntas", [])
    faltantes = faltantes or []
    if any(
        SECRETOS.search(_normalizar(item))
        for item in [*preguntas, *faltantes]
        if isinstance(item, str)
    ):
        return True

    texto = borrador.get("texto", "")
    if not isinstance(texto, str):
        return False
    for frase in re.split(r"[.!?\n]", _normalizar(texto)):
        for pedido in PEDIDOS.finditer(frase):
            antes = frase[max(0, pedido.start() - 12):pedido.start()]
            if re.search(r"\b(?:no|nunca|jamas)\s+$", antes):
                continue
            if SECRETOS.search(frase[pedido.end():pedido.end() + 100]):
                return True
    return False
