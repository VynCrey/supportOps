import re
import unicodedata


SECRETOS = re.compile(
    r"\b(?:token(?:s)?|contrasena(?:s)?|password|claves?|"
    r"api[ _-]?key|secretos?|otp|codigo(?:s)? de (?:verificacion|"
    r"autenticacion|seguridad)|2fa)\b"
)
PEDIDOS = re.compile(
    r"\b(?:envia\w*|manda\w*|comparte\w*|comparti\w*|proporciona\w*|"
    r"facilita\w*|indica\w*|dime|deci\w*|muestra\w*|copia\w*|pega\w*|"
    r"pasa\w*|escrib\w*|das|dame|dar|des|entrega\w*|revela\w*|"
    r"adjunta\w*|subi\w*|necesit\w*|solicit\w*)\b"
)
OBJETO_DIRECTO = {
    "me", "nos", "tu", "su", "el", "la", "los", "las", "un", "una",
    "aca", "aqui", "por", "favor", "valor", "de", "del", "en",
    "este", "campo", "foto", "captura", "imagen", "copia",
    "actual", "completo", "exacto", "vigente", "original", "nuevo",
    "ultimos", "primeros", "caracteres", "digitos",
}
OBJETO_ADICIONAL = re.compile(
    r"\by\s+(?:(?:el|la)\s+)?(?:valor\s+(?:actual\s+)?de\s+)?"
    r"(?:tu|su|el|la)\s*$"
)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(letra for letra in texto if not unicodedata.combining(letra))


def _pide_secreto(texto: str) -> bool:
    """Distingue pedir el secreto de mencionar un token para diagnosticarlo."""
    for frase in re.split(r"[.!?\n]", _normalizar(texto)):
        pregunta = re.search(r"\bcual es (?:tu|su|el|la)\s+", frase)
        if pregunta and SECRETOS.match(frase[pregunta.end():]):
            return True
        for pedido in PEDIDOS.finditer(frase):
            antes = frase[max(0, pedido.start() - 12):pedido.start()]
            if re.search(r"\b(?:no|nunca|jamas|sin)\s+$", antes):
                continue
            for secreto in SECRETOS.finditer(frase, pedido.end()):
                entre = frase[pedido.end():secreto.start()]
                if len(entre) > 100:
                    break
                # Solo se bloquea si el secreto es el objeto del pedido.
                # "Proporciona la hora del error sin incluir el token" pide
                # una hora, no el valor del token.
                entre = re.sub(r"[,;:]", " ", entre).strip()
                if (all(palabra in OBJETO_DIRECTO or palabra.isdecimal()
                        for palabra in entre.split())
                        or OBJETO_ADICIONAL.search(entre)):
                    return True
    return False


def pide_credenciales(borrador: dict, faltantes: list[str] | None = None) -> bool:
    """Detecta pedidos de secretos en texto, preguntas y datos faltantes."""
    campos = [borrador.get("texto", ""), *(borrador.get("preguntas") or []),
              *(faltantes or [])]
    return any(_pide_secreto(item) for item in campos if isinstance(item, str))
