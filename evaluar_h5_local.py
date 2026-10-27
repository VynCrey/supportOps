"""Ejecuta una vez cada caso H5 pendiente contra la API local.

Guarda el ID del ticket antes de analizarlo para poder reanudar sin duplicarlo.
No registra revisiones humanas ni modifica la aplicación o la base de conocimiento.
"""

import csv
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


RAIZ = Path(__file__).resolve().parent
CSV = RAIZ / "docs" / "eval" / "tickets_h5.csv"
OBSERVACIONES = RAIZ / "docs" / "eval" / "h5_observaciones.json"
API = os.getenv("SUPPORTOPS_API_URL", "http://127.0.0.1:8000").rstrip("/")


def llamar(metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = Request(
        API + ruta,
        data=datos,
        headers={"Content-Type": "application/json"} if datos is not None else {},
        method=metodo,
    )
    try:
        with urlopen(peticion, timeout=180) as respuesta:
            return json.load(respuesta)
    except HTTPError as error:
        raise RuntimeError(f"{ruta}: HTTP {error.code}: {error.read().decode('utf-8')}") from error


def leer_filas() -> tuple[list[str], list[dict[str, str]]]:
    with CSV.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        return list(lector.fieldnames or []), list(lector)


def guardar_filas(campos: list[str], filas: list[dict[str, str]]) -> None:
    temporal = CSV.with_suffix(".csv.tmp")
    with temporal.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    temporal.replace(CSV)


def guardar_observaciones(datos: dict) -> None:
    temporal = OBSERVACIONES.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(OBSERVACIONES)


def decision_aceptable(esperado: str, obtenido: str) -> bool:
    esperado = esperado.casefold()
    if "no bloquear" in esperado and obtenido == "bloquear":
        return False
    if esperado.startswith("revisar (seguridad"):
        return obtenido == "revisar"
    if esperado == "revisar":
        return obtenido == "revisar"
    return obtenido in esperado.split(" (")[0].split(" o ")


def procesar() -> None:
    campos, filas = leer_filas()
    observaciones = json.loads(OBSERVACIONES.read_text(encoding="utf-8")) if OBSERVACIONES.exists() else {}
    for fila in filas:
        numero = int(fila["id"][1:])
        if numero > 20:
            continue
        if not fila["ticket_id"]:
            ticket = llamar("POST", "/tickets", {
                "cliente_id": int(fila["cliente_id"]),
                "texto": fila["texto"],
            })
            fila["ticket_id"] = str(ticket["id"])
            guardar_filas(campos, filas)
            print(f'{fila["id"]}: creado ticket {ticket["id"]}', flush=True)
        ticket = llamar("GET", f'/tickets/{fila["ticket_id"]}')
        if ticket["texto"] != fila["texto"] or ticket["cliente_id"] != int(fila["cliente_id"]):
            raise RuntimeError(f'{fila["id"]}: el ticket guardado no coincide con el caso reservado')
        if not fila["ejecucion_id"]:
            resultado = llamar("POST", f'/tickets/{fila["ticket_id"]}/analizar')
            fila["ejecucion_id"] = str(resultado["ejecucion_id"])
            guardar_filas(campos, filas)
            print(f'{fila["id"]}: ejecución {fila["ejecucion_id"]}', flush=True)
        ejecucion = llamar("GET", f'/ejecuciones/{fila["ejecucion_id"]}')
        if ejecucion["ticket_id"] != int(fila["ticket_id"]):
            raise RuntimeError(f'{fila["id"]}: la ejecución pertenece a otro ticket')
        resultado = ejecucion["resultado"]
        categoria = resultado["triage"]["categoria"]
        documentos = [item["id"] for item in resultado.get("evidencia", [])]
        decision = resultado["supervision"]["decision"]
        citas = resultado["borrador"].get("citas", [])
        aceptables = set(fila["documentos_aceptables"].split("|")) if fila["documentos_aceptables"] else set()
        comprobaciones = {
            "categoria": categoria == fila["categoria_esperada"],
            "documentos": bool(aceptables.intersection(documentos)) if aceptables else not citas,
            "decision": decision_aceptable(fila["decision_esperada"], decision),
        }
        fila["categoria_obtenida"] = categoria
        fila["documentos_obtenidos"] = "|".join(documentos)
        fila["decision_obtenida"] = decision
        fila["cumple"] = "si" if all(comprobaciones.values()) else "no"
        observaciones[fila["id"]] = {
            "ticket_id": int(fila["ticket_id"]),
            "ejecucion_id": int(fila["ejecucion_id"]),
            "categoria": categoria,
            "documentos": documentos,
            "citas": citas,
            "decision": decision,
            "borrador": resultado["borrador"],
            "supervision": resultado["supervision"],
            "comprobaciones": comprobaciones,
        }
        guardar_filas(campos, filas)
        guardar_observaciones(observaciones)
        print(f'{fila["id"]}: {categoria}, {"|".join(documentos)}, {decision}, cumple={fila["cumple"]}', flush=True)


if __name__ == "__main__":
    procesar()
