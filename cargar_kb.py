"""Carga kb.json en las tablas documentos y relaciones de PostgreSQL.
Uso:  python cargar_kb.py            (pide la contrasena; requiere bootstrap.py antes)

Idempotente: se puede correr muchas veces. kb.json sale del laboratorio de Marco
(exportar_kb.py), que es donde la KB se edita y se mide. Un documento cuyo
contenido cambio se actualiza con la version que trae kb.json. Las relaciones
solo se agregan: si se quita una de kb.json, hay que borrarla a mano.
"""
import json
from getpass import getpass
from pathlib import Path

KB = Path(__file__).with_name("kb.json")
CAMPOS = ("id", "categoria", "titulo", "version", "texto")


def leer_archivo(ruta: Path = KB) -> dict:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    validar(datos)
    return datos


def validar(datos: dict) -> None:
    """Frena un kb.json roto antes de tocar la base."""
    documentos, relaciones = datos["documentos"], datos["relaciones"]
    ids = [d["id"] for d in documentos]
    if len(ids) != len(set(ids)):
        raise ValueError("Hay IDs de documento repetidos")
    for d in documentos:
        if set(d) != set(CAMPOS):
            raise ValueError(f"{d.get('id')}: campos distintos de {CAMPOS}")
        if not isinstance(d["version"], int) or d["version"] < 1:
            raise ValueError(f"{d['id']}: la version debe ser un entero positivo")
    existentes = set(ids)
    for r in relaciones:
        if set(r) != {"origen", "relacion", "destino"}:
            raise ValueError(f"Relacion mal formada: {r}")
        # Toda punta que parece un documento tiene que existir.
        for punta in (r["origen"], r["destino"]):
            if punta.startswith("KB-") and punta not in existentes:
                raise ValueError(f"La relacion {r} apunta a un documento que no existe")


def cargar(conexion, datos: dict) -> dict:
    nuevos = actualizados = iguales = relaciones_nuevas = 0
    with conexion.cursor() as cursor:
        for d in datos["documentos"]:
            cursor.execute(
                "SELECT categoria, titulo, version, texto FROM documentos WHERE id = %s",
                (d["id"],),
            )
            fila = cursor.fetchone()
            if fila is None:
                cursor.execute(
                    "INSERT INTO documentos (id, categoria, titulo, version, texto) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    tuple(d[c] for c in CAMPOS),
                )
                nuevos += 1
            elif dict(fila) != {c: d[c] for c in CAMPOS if c != "id"}:
                cursor.execute(
                    "UPDATE documentos SET categoria = %s, titulo = %s, version = %s, "
                    "texto = %s WHERE id = %s",
                    (d["categoria"], d["titulo"], d["version"], d["texto"], d["id"]),
                )
                actualizados += 1
            else:
                iguales += 1
        for r in datos["relaciones"]:
            cursor.execute(
                "INSERT INTO relaciones (origen, relacion, destino) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (r["origen"], r["relacion"], r["destino"]),
            )
            relaciones_nuevas += cursor.rowcount
    return {"nuevos": nuevos, "actualizados": actualizados, "sin cambios": iguales,
            "relaciones nuevas": relaciones_nuevas}


def main() -> None:
    from db import SupportOpsDB

    datos = leer_archivo()
    clave = getpass("Contrasena de PostgreSQL: ")
    # Una sola transaccion: si algo falla, no queda una KB a medio cargar.
    with SupportOpsDB(clave).conectar() as conexion:
        print(cargar(conexion, datos))


if __name__ == "__main__":
    main()
