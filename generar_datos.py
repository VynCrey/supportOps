"""Completa la base ficticia hasta 500 clientes, 20.000 tickets y 60.000 eventos.

Sin --aplicar muestra el plan. Requiere ejecutar bootstrap.py primero.
"""

import argparse
from getpass import getpass
from random import Random

import psycopg

from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER


OBJETIVO_CLIENTES = 500
OBJETIVO_TICKETS = 20_000
OBJETIVO_EVENTOS = 60_000
SEMILLA = 42

# Tres familias por categoria, tres formas de contar cada problema.
FAMILIAS = {
    "acceso": (
        ("No puedo entrar a mi cuenta", "El inicio de sesion falla", "Mi usuario no logra ingresar"),
        ("La cuenta quedo bloqueada", "Se bloqueo mi acceso", "El sistema rechaza mi cuenta"),
        ("No llega el codigo de acceso", "Falta el segundo factor", "No recibo el codigo de ingreso"),
    ),
    "facturacion": (
        ("No encuentro la factura", "Mi factura no aparece", "Falta la factura del mes"),
        ("Veo un cobro duplicado", "Me cobraron dos veces", "Hay un cargo repetido"),
        ("El importe de mi plan no coincide", "La factura muestra otro plan", "El precio facturado parece incorrecto"),
    ),
    "api": (
        ("La API devuelve error 401", "Recibo 401 en un endpoint", "Una llamada a la API responde 401"),
        ("La API devuelve error 429", "Mis peticiones reciben 429", "Al consultar el endpoint aparece 429"),
        ("El webhook no recibe eventos", "Fallan las notificaciones por webhook", "El webhook no entrega la respuesta"),
    ),
    "exportacion": (
        ("No puedo descargar el CSV", "La exportacion CSV falla", "El archivo CSV no aparece"),
        ("El PDF exportado esta vacio", "La descarga PDF no tiene datos", "Mi PDF sale en blanco"),
        ("La exportacion tarda demasiado", "La descarga vence por tiempo", "El archivo no termina de generarse"),
    ),
    "notificaciones": (
        ("No recibo avisos por correo", "Faltan los correos de aviso", "Las alertas por email no llegan"),
        ("No aparecen notificaciones en la app", "La app no muestra alertas", "Faltan avisos dentro de la aplicacion"),
        ("Recibo alertas repetidas", "Una notificacion llega dos veces", "Los avisos se duplican"),
    ),
    "seguridad": (
        ("Veo un acceso desconocido", "Hay un ingreso que no reconozco", "Aparece una sesion ajena"),
        ("Me llego un cambio de clave inesperado", "No pedi restablecer la clave", "Recibi un aviso de cambio de contrasena"),
        ("Mis permisos cambiaron sin aviso", "Veo un rol que no solicite", "Mi cuenta tiene permisos inesperados"),
    ),
}

PESOS = (22, 16, 20, 16, 18, 8)


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

    rng = Random(SEMILLA)
    categorias = tuple(FAMILIAS)
    clientes_nuevos = []
    textos = []
    categorias_nuevas = []
    familias_nuevas = []
    prioridades = []
    for n in range(1, tickets_faltantes + 1):
        categoria = rng.choices(categorias, weights=PESOS)[0]
        familia_indice = rng.randrange(3)
        texto = rng.choice(FAMILIAS[categoria][familia_indice])
        clientes_nuevos.append(rng.choice(clientes_ids))
        textos.append(f"{texto} (caso de prueba #{cantidades['tickets'] + n})")
        categorias_nuevas.append(categoria)
        familias_nuevas.append(f"{categoria}-{familia_indice + 1}")
        prioridades.append("alta" if categoria in ("api", "seguridad") else "media")

    cursor.execute(
        """
        WITH base AS (
            SELECT n, cliente_id, texto, categoria, familia, prioridad,
                   TIMESTAMPTZ '2026-09-02 00:00:00+00'
                       + n * INTERVAL '1 minute' AS creado
            FROM unnest(%s::bigint[], %s::text[], %s::text[],
                        %s::text[], %s::text[])
                 WITH ORDINALITY AS entrada(cliente_id, texto, categoria,
                                           familia, prioridad, n)
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
               texto,
               categoria,
               familia,
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
        (clientes_nuevos, textos, categorias_nuevas, familias_nuevas, prioridades),
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
