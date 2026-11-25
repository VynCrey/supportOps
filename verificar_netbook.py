"""Comprueba que la demostracion local este lista, sin usar contrasenas."""

import json
import subprocess
from urllib.error import URLError
from urllib.request import urlopen


API = "http://127.0.0.1:8000"


def leer_json(ruta: str) -> dict:
    with urlopen(API + ruta, timeout=4) as respuesta:
        return json.load(respuesta)


def comprobar() -> int:
    fallos = 0
    try:
        salud = leer_json("/health")
        if salud.get("estado") != "ok" or salud.get("base") != "conectada":
            raise ValueError("la API no confirmó la conexión a PostgreSQL")
        print("OK  API y PostgreSQL conectados")
        productos = leer_json("/productos").get("productos", [])
        if not productos:
            raise ValueError("el catalogo ficticio esta vacio")
        print(f"OK  Catalogo ficticio: {len(productos)} productos")
    except (URLError, TimeoutError, ValueError, OSError):
        print("FALTA  API o datos locales.")
        print("       Abri 02_INICIAR_API.cmd y comproba PostgreSQL.")
        fallos += 1

    try:
        modelo = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True,
            timeout=10, check=True,
        )
        if "qwen2.5:3b" not in modelo.stdout:
            raise ValueError("no aparece qwen2.5:3b")
        print("OK  Ollama y modelo qwen2.5:3b disponibles")
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        print("FALTA  Ollama o el modelo qwen2.5:3b.")
        print("       Abri Ollama; si falta el modelo, ejecuta ollama pull qwen2.5:3b.")
        fallos += 1

    for nombre, puerto, archivo in (
        ("Soporte", 8501, "03_ABRIR_PANEL.cmd"),
        ("Cliente", 8502, "04_ABRIR_CLIENTE.cmd"),
    ):
        try:
            with urlopen(f"http://127.0.0.1:{puerto}", timeout=4) as respuesta:
                if respuesta.status != 200:
                    raise ValueError(f"HTTP {respuesta.status}")
            print(f"OK  Pantalla de {nombre.lower()} en http://127.0.0.1:{puerto}")
        except (URLError, TimeoutError, ValueError, OSError):
            print(f"FALTA  Pantalla de {nombre.lower()}: abri {archivo}.")
            fallos += 1

    if fallos:
        print(f"\nFaltan {fallos} comprobaciones. Corregi los puntos indicados y repeti.")
        return 1
    print("\nDemostracion local lista. Abri las dos direcciones indicadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(comprobar())
