"""Resumen descriptivo de la base local. No modifica registros."""

from getpass import getpass

import psycopg

from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER


def main() -> None:
    clave = getpass("Contrasena de PostgreSQL: ")
    with psycopg.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=clave,
    ) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM clientes")
            clientes = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM tickets")
            tickets = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM eventos")
            eventos = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT familia) FROM tickets")
            familias = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT categoria_real, COUNT(*) AS cantidad
                FROM tickets
                WHERE categoria_real IS NOT NULL
                GROUP BY categoria_real
                ORDER BY cantidad DESC, categoria_real
                LIMIT 1
                """
            )
            categoria_principal = cursor.fetchone()

            cursor.execute("SELECT estado, COUNT(*) FROM tickets GROUP BY estado")
            estados = dict(cursor.fetchall())

            cursor.execute(
                """
                SELECT percentile_cont(0.5) WITHIN GROUP (
                           ORDER BY (EXTRACT(EPOCH FROM
                               (primera_respuesta - creado)) / 60.0)::float8
                       ),
                       percentile_cont(0.9) WITHIN GROUP (
                           ORDER BY (EXTRACT(EPOCH FROM
                               (primera_respuesta - creado)) / 60.0)::float8
                       ),
                       percentile_cont(0.5) WITHIN GROUP (
                           ORDER BY (EXTRACT(EPOCH FROM
                               (resuelto - creado)) / 60.0)::float8
                       ),
                       percentile_cont(0.9) WITHIN GROUP (
                           ORDER BY (EXTRACT(EPOCH FROM
                               (resuelto - creado)) / 60.0)::float8
                       )
                FROM tickets
                """
            )
            tiempos = cursor.fetchone()

            cursor.execute(
                """
                SELECT COUNT(*) FROM tickets
                WHERE primera_respuesta < creado OR resuelto < creado
                   OR (resuelto IS NOT NULL AND estado <> 'resuelto')
                """
            )
            incoherentes = cursor.fetchone()[0]
            cursor.execute("SELECT decision, COUNT(*) FROM revisiones GROUP BY decision")
            revisiones = dict(cursor.fetchall())

    print(f"Volumen: {clientes} clientes, {tickets} tickets, {eventos} eventos.")
    print(f"Familias registradas: {familias}. Fechas/estados incoherentes: {incoherentes}.")
    if categoria_principal:
        nombre, cantidad = categoria_principal
        print(f"Hallazgo 1: la categoria mas frecuente es {nombre} ({cantidad} tickets).")
    if tickets:
        abiertos = estados.get("abierto", 0)
        print(f"Hallazgo 2: {abiertos} tickets siguen abiertos ({100 * abiertos / tickets:.1f} %).")
    if tiempos[0] is not None:
        print(
            f"Hallazgo 3: primera respuesta mediana {tiempos[0]:.1f} min; "
            f"percentil 90 {tiempos[1]:.1f} min."
        )
    if tiempos[2] is not None:
        print(f"Resolucion: mediana {tiempos[2]:.1f} min; percentil 90 {tiempos[3]:.1f} min.")
    print("Revisiones registradas:", revisiones)
    print("Limite: son datos ficticios y repetitivos; estas cifras no describen una empresa real.")


if __name__ == "__main__":
    main()
