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


def motivo_consulta_restringida(texto: str) -> str | None:
    """Bloquea pedidos explícitos de datos internos e instrucciones inyectadas."""
    normal = _normalizar(texto)
    if re.search(
        r"\b(?:dame|mostra\w*|muestra\w*|envia\w*|pasame|exporta\w*|"
        r"descarga\w*|entrega\w*)\b.{0,80}"
        r"\b(?:(?:toda\s+)?(?:tu|la)\s+base\s+de\s+datos|"
        r"todos\s+los\s+(?:clientes|tickets|pedidos|chats|mensajes)|"
        r"todas\s+las\s+(?:conversaciones|consultas)|"
        r"(?:el|los)\s+(?:chat|mensajes|conversacion)\s+"
        r"(?:de|del)\s+(?:(?:otro|otra|un|una|el|la)\s+)?(?:cliente|usuario)|"
        r"tabla\s+(?:completa|de\s+clientes)|"
        r"(?:los\s+)?datos\s+(?:de|del)\s+(?:otro\s+)?(?:cliente|usuario)|"
        r"(?:contrase[nñ]as?|claves?|tokens?)\s+(?:de|del)\s+"
        r"(?:(?:un|una|el|la)\s+)?(?:cliente|usuario))\b",
        normal,
    ):
        return "Solicitud de datos internos o masivos"
    if re.search(
        r"\b(?:ignora\w*|olvida\w*|desobedece\w*)\b.{0,70}"
        r"\b(?:instrucciones|reglas|sistema|prompt)\b|"
        r"\b(?:actua|responde)\s+como\s+(?:el\s+)?(?:sistema|administrador)\b|"
        r"\b(?:system|developer|assistant)\s*:|<\|(?:system|developer|assistant)\|>|"
        r"\[inst\]",
        normal,
    ):
        return "Instrucciones no confiables en la consulta"
    return None
