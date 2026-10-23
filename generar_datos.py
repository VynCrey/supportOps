"""Completa la base ficticia hasta 500 clientes, 20.000 tickets y 60.000 eventos.

Sin --aplicar muestra el plan. Requiere ejecutar bootstrap.py primero.
"""

import argparse
from getpass import getpass

import psycopg

from bootstrap import CASOS
from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER


OBJETIVO_CLIENTES = 500
OBJETIVO_TICKETS = 20_000
OBJETIVO_EVENTOS = 60_000


def contar(cursor) -> dict[str, int]:
    cantidades = {}
    for tabla in ("clientes", "tickets", "eventos"):
        cursor.execute(f"SELECT count(*) FROM {tabla}")
        cantidades[tabla] = cursor.fetchone()[0]
    return cantidades


def validar(cantidades: dict[str, int]) -> None:
    if cantidades["clientes"] < 1:
        raise ValueError("Primero ejecuta bootstrap.py para crear la muestra")
    if cantidades["clientes"] > OBJETIVO_CLIENTES or cantidades["tickets"] > OBJETIVO_TICKETS:
        raise ValueError("La base ya supera el volumen objetivo; no se modifico")
    if cantidades["eventos"] != 3 * cantidades["tickets"]:
        raise ValueError("Los eventos no son tres por ticket; revisa la base antes de generar")


def completar(cursor, cantidades: dict[str, int]) -> None:
    clientes_faltantes = OBJETIVO_CLIENTES - cantidades["clientes"]
    if clientes_faltantes:
        cursor.execute(
            """
            INSERT INTO clientes (nombre, plan)
            SELECT 'Cliente sintetico ' || (%s + n),
                   (ARRAY['Basic', 'Pro', 'Enterprise'])[mod(n - 1, 3) + 1]
            FROM generate_series(1, %s) AS serie(n)
            """,
            (cantidades["clientes"], clientes_faltantes),
        )

    cursor.execute("SELECT array_agg(id ORDER BY id) FROM clientes")
    clientes_ids = cursor.fetchone()[0]
    tickets_faltantes = OBJETIVO_TICKETS - cantidades["tickets"]
    if not tickets_faltantes:
        return

    textos = [caso[0] for caso in CASOS]
    categorias = [caso[1] for caso in CASOS]
    prioridades = [caso[2] for caso in CASOS]
    cursor.execute(
        """
        WITH base AS (
            SELECT n,
                   (%s::bigint[])[mod(n - 1, %s) + 1] AS cliente_id,
                   (%s::text[])[mod(n - 1, 6) + 1] AS texto_base,
                   (%s::text[])[mod(n - 1, 6) + 1] AS categoria,
                   (%s::text[])[mod(n - 1, 6) + 1] AS prioridad,
                   TIMESTAMPTZ '2026-01-01 00:00:00+00'
                       + n * INTERVAL '10 minutes' AS creado
            FROM generate_series(1, %s) AS serie(n)
        ),
        tiempos AS (
            SELECT *, creado + (5 + mod(n, 110)) * INTERVAL '1 minute'
                      AS respondido
            FROM base
        )
        INSERT INTO tickets
            (cliente_id, texto, categoria_real, familia, prioridad,
             estado, creado, primera_respuesta, resuelto)
        SELECT cliente_id,
               texto_base || ' (caso de prueba #' || n || ')',
               categoria,
               categoria || '-' || mod(n, 4),
               prioridad,
               CASE WHEN mod(n, 5) IN (0, 1) THEN 'resuelto' ELSE 'abierto' END,
               creado,
               respondido,
               CASE WHEN mod(n, 5) IN (0, 1)
                    THEN respondido + (30 + mod(n, 240)) * INTERVAL '1 minute'
                    ELSE NULL END
        FROM tiempos
        RETURNING id, creado, primera_respuesta, resuelto
        """,
        (clientes_ids, len(clientes_ids), textos, categorias, prioridades,
         tickets_faltantes),
    )
    nuevos = cursor.fetchall()
    with cursor.copy("COPY eventos (ticket_id, tipo, momento) FROM STDIN") as copia:
        for ticket_id, creado, respondido, resuelto in nuevos:
            copia.write_row((ticket_id, "creado", creado))
            copia.write_row((ticket_id, "respondido", respondido))
            copia.write_row(
                (ticket_id, "resuelto" if resuelto else "asignado", resuelto or respondido)
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true", help="Inserta los datos ficticios")
    argumentos = parser.parse_args()
    clave = getpass("Contrasena de PostgreSQL: ")
    with psycopg.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=clave,
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('supportops_generador'))")
            antes = contar(cursor)
            validar(antes)
            print("Cantidades actuales:", antes)
            print("Objetivo:", {
                "clientes": OBJETIVO_CLIENTES,
                "tickets": OBJETIVO_TICKETS,
                "eventos": OBJETIVO_EVENTOS,
            })
            if not argumentos.aplicar:
                print("Vista previa. Para insertar, ejecuta con --aplicar.")
                return
            completar(cursor, antes)
            despues = contar(cursor)
            if despues != {
                "clientes": OBJETIVO_CLIENTES,
                "tickets": OBJETIVO_TICKETS,
                "eventos": OBJETIVO_EVENTOS,
            }:
                raise RuntimeError(f"Conteos inesperados: {despues}")
            print("Datos generados:", despues)


if __name__ == "__main__":
    main()
