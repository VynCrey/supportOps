from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path

import psycopg
from psycopg import sql

from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER


SCHEMA = Path(__file__).with_name("schema.sql")

CLIENTES = (
    ("Cliente demo 1", "Basic"),
    ("Cliente demo 2", "Pro"),
    ("Cliente demo 3", "Enterprise"),
)

CASOS = (
    ("No puedo entrar con mi contrasena", "acceso", "media"),
    ("No encuentro mi factura de este mes", "facturacion", "media"),
    ("La API devuelve error 401 con el token", "api", "alta"),
    ("No puedo descargar mi archivo CSV", "exportacion", "baja"),
    ("No recibo notificaciones por correo", "notificaciones", "baja"),
    ("Veo un acceso desconocido a mi cuenta", "seguridad", "alta"),
)


def crear_base_si_falta(clave: str) -> None:
    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname="postgres",
        user=DB_USER,
        password=clave,
        autocommit=True,
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DB_NAME,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME))
                )
                print(f"Base {DB_NAME} creada.")
            else:
                print(f"Base {DB_NAME} ya existe.")


def aplicar_esquema(cursor) -> None:
    for sentencia in SCHEMA.read_text(encoding="utf-8").split(";"):
        if sentencia.strip():
            cursor.execute(sentencia)


def cargar_muestra(cursor) -> bool:
    cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM clientes) OR EXISTS (SELECT 1 FROM tickets)"
    )
    if cursor.fetchone()[0]:
        return False

    clientes_ids = []
    for nombre, plan in CLIENTES:
        cursor.execute(
            "INSERT INTO clientes (nombre, plan) VALUES (%s, %s) RETURNING id",
            (nombre, plan),
        )
        clientes_ids.append(cursor.fetchone()[0])

    inicio = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for numero, (texto, categoria, prioridad) in enumerate(CASOS):
        creado = inicio + timedelta(hours=numero)
        respondido = creado + timedelta(minutes=15)
        resuelto = respondido + timedelta(minutes=30) if numero in (1, 3) else None
        estado = "resuelto" if resuelto else "abierto"

        cursor.execute(
            """
            INSERT INTO tickets
                (cliente_id, texto, categoria_real, familia, prioridad,
                 estado, creado, primera_respuesta, resuelto)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                clientes_ids[numero % len(clientes_ids)],
                texto,
                categoria,
                f"{categoria}-demo",
                prioridad,
                estado,
                creado,
                respondido,
                resuelto,
            ),
        )
        ticket_id = cursor.fetchone()[0]
        eventos = (
            ("creado", creado),
            ("respondido", respondido),
            ("resuelto", resuelto) if resuelto else ("asignado", respondido),
        )
        for tipo, momento in eventos:
            cursor.execute(
                "INSERT INTO eventos (ticket_id, tipo, momento) VALUES (%s, %s, %s)",
                (ticket_id, tipo, momento),
            )
    return True


def main() -> None:
    clave = getpass("Contrasena de PostgreSQL: ")
    crear_base_si_falta(clave)

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=clave,
    ) as conexion:
        with conexion.cursor() as cursor:
            aplicar_esquema(cursor)
            creada = cargar_muestra(cursor)
            cantidades = {}
            for tabla in ("clientes", "tickets", "eventos", "documentos"):
                cursor.execute(
                    sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
                )
                cantidades[tabla] = cursor.fetchone()[0]

    print("Muestra cargada." if creada else "Ya habia datos; no se duplicaron.")
    print("Cantidades:", cantidades)


if __name__ == "__main__":
    main()
