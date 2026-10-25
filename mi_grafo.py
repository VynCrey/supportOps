"""Consulta del grafo por sintoma, con ruta visible y maximo dos saltos.
Uso:  python mi_grafo.py "Codigo 401 al autenticar"     (pide la contrasena)

ruta() recibe documentos y relaciones como listas y no toca la base, asi se
prueba sin PostgreSQL. Solo el modo de linea de comandos lee la base.
"""
import re
import sys
import unicodedata
from getpass import getpass

MAX_SALTOS = 2
TOP_K = 3
# Una ruta causal es mas especifica que una ruta por categoria.
PESO = {"procedimiento": 0, "documenta": 2, "reemplaza_a": 9}
# Palabras que no cuentan como clave de un sintoma ('cambio_de_email').
NO_CLAVE = {"de", "del", "la", "el", "en", "por", "con", "no", "y"}


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def resolver_nodo(texto: str, nodos: set[str]) -> str | None:
    """Nodo de arranque: el nombre exacto, despues un codigo numerico, despues
    una palabra que coincida con el nombre de un sintoma."""
    if texto.strip() in nodos:
        return texto.strip()
    for codigo in re.findall(r"\d{3}", normalizar(texto)):
        if f"sintoma:{codigo}" in nodos:
            return f"sintoma:{codigo}"
    palabras = re.findall(r"\w+", normalizar(texto))
    candidatos = [n for n in sorted(nodos)
                  if n.startswith("sintoma:") and coincide(n, palabras)]
    # Si coinciden varios, gana el mas especifico: el de mas palabras clave.
    return max(candidatos, key=lambda n: len(palabras_clave(n)), default=None)


def palabras_clave(nodo: str) -> list[str]:
    """'sintoma:pago_rechazado' -> ['pago', 'rechazado']."""
    return [p for p in nodo.split(":", 1)[1].split("_") if p and p not in NO_CLAVE]


def coincide(nodo: str, palabras: list[str]) -> bool:
    """El sintoma arranca solo si TODAS sus palabras clave estan en la consulta.
    Acepta plural o sufijo: 'webhooks' coincide con 'webhook'. Antes alcanzaba con
    que una palabra de la consulta fuera parte del nombre ('la' en 'clave')."""
    claves = palabras_clave(nodo)
    return bool(claves) and all(any(p == c or p.startswith(c) for p in palabras)
                                for c in claves)


def ruta(texto: str, documentos: list[dict], relaciones: list[dict],
         max_saltos: int = MAX_SALTOS, k: int = TOP_K) -> dict:
    salientes = {}
    for r in sorted(relaciones, key=lambda r: (r["origen"], r["relacion"], r["destino"])):
        salientes.setdefault(r["origen"], []).append((r["relacion"], r["destino"]))
    inicio = resolver_nodo(texto, set(salientes))
    if inicio is None:
        return {"nodo": None, "documentos": []}
    docs = {d["id"] for d in documentos}
    # Un documento reemplazado por otro no se devuelve: no es la version vigente.
    retirados = {r["destino"] for r in relaciones if r["relacion"] == "reemplaza_a"}
    encontrados, visitados = {}, {inicio}
    frontera = [(inicio, inicio)]
    for salto in range(1, max_saltos + 1):
        siguiente = []
        for nodo, camino in frontera:
            for paso, destino in salientes.get(nodo, []):
                nuevo = f"{camino} --{paso}--> {destino}"
                if destino in docs:
                    if destino in retirados:
                        continue
                    hallazgo = {"id": destino, "saltos": salto,
                                "peso": PESO.get(paso, 5), "camino": nuevo}
                    previo = encontrados.get(destino)
                    # Se guarda la MEJOR ruta, no la primera que aparece.
                    if previo is None or (hallazgo["peso"], hallazgo["saltos"]) < (
                            previo["peso"], previo["saltos"]):
                        encontrados[destino] = hallazgo
                elif destino not in visitados:
                    visitados.add(destino)
                    siguiente.append((destino, nuevo))
        frontera = siguiente
    orden = sorted(encontrados.values(), key=lambda d: (d["peso"], d["saltos"], d["id"]))
    return {"nodo": inicio, "documentos": orden[:k]}


if __name__ == "__main__":
    from retrieval import leer_kb

    consulta = sys.argv[1] if len(sys.argv) > 1 else "Codigo 401 al autenticar"
    documentos, relaciones = leer_kb(getpass("Contrasena de PostgreSQL: "))
    salida = ruta(consulta, documentos, relaciones)
    print("consulta:", consulta)
    print("nodo de arranque:", salida["nodo"] or "ninguno (el grafo no cubre el sintoma)")
    if not salida["documentos"]:
        print("Sin documentos por esta ruta. El sistema debe pedir datos, no inventar.")
    for d in salida["documentos"]:
        print(f"  {d['id']}  ({d['saltos']} saltos)  <-  {d['camino']}")
