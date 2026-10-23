"""Punto de union con retrieval.py de Marco.

Mientras ese modulo no exista, devuelve evidencia vacia. El resultado del
analisis deja constancia de esta limitacion para el operador.
"""

try:
    from retrieval import retrieve as _retrieve_de_marco
except ModuleNotFoundError as error:
    if error.name != "retrieval":
        raise
    _retrieve_de_marco = None


KB_CONECTADA = _retrieve_de_marco is not None


def retrieve(query: str, category: str, tool: str) -> list[dict]:
    if tool not in ("lexical", "grafo", "hibrido"):
        raise ValueError("Herramienta de busqueda no permitida")
    if _retrieve_de_marco is None:
        return []
    return _retrieve_de_marco(query, category, tool)
