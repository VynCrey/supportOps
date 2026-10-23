"""Cliente HTTP pequeño para la interfaz local de SupportOps."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = os.getenv("SUPPORTOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")


class APIError(Exception):
    pass


def solicitar(metodo: str, ruta: str, *, parametros: dict | None = None,
              cuerpo: dict | None = None, timeout: int = 15) -> dict:
    url = API_URL + ruta
    if parametros:
        url += "?" + urlencode(parametros)
    contenido = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    solicitud = Request(
        url,
        data=contenido,
        headers={"Content-Type": "application/json"} if contenido is not None else {},
        method=metodo,
    )
    try:
        with urlopen(solicitud, timeout=timeout) as respuesta:
            return json.load(respuesta)
    except HTTPError as error:
        try:
            detalle = json.load(error).get("detail", "Error de la API")
        except (ValueError, OSError):
            detalle = "Error de la API"
        raise APIError(f"HTTP {error.code}: {detalle}") from error
    except (URLError, TimeoutError) as error:
        raise APIError("No se pudo conectar con la API local") from error


def get(ruta: str, **parametros) -> dict:
    return solicitar("GET", ruta, parametros=parametros)


def post(ruta: str, cuerpo: dict | None = None, timeout: int = 15) -> dict:
    return solicitar("POST", ruta, cuerpo=cuerpo, timeout=timeout)
