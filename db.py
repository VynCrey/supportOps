import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER
from safety import pide_credenciales


class SupportOpsDB:
    def __init__(self, clave: str):
        self.clave = clave

    def conectar(self):
        return psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=self.clave,
            row_factory=dict_row,
        )

    def comprobar(self):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

    def listar_clientes(self):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id, nombre, plan FROM clientes ORDER BY id")
                return cursor.fetchall()

    def contar_tickets(self, plan: str | None = None):
        consulta = "SELECT COUNT(*) AS cantidad FROM tickets AS t"
        parametros = ()
        if plan is not None:
            consulta += " JOIN clientes AS c ON c.id = t.cliente_id WHERE c.plan = %s"
            parametros = (plan,)
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, parametros)
                return cursor.fetchone()["cantidad"]

    def listar_tickets(self, plan: str | None = None, limit: int = 50,
                       offset: int = 0):
        consulta = """
            SELECT t.id, t.cliente_id, c.nombre AS cliente, c.plan,
                   t.texto, t.prioridad, t.estado, t.creado
            FROM tickets AS t
            JOIN clientes AS c ON c.id = t.cliente_id
        """
        parametros = ()
        if plan is not None:
            consulta += " WHERE c.plan = %s"
            parametros = (plan,)
        consulta += " ORDER BY t.id LIMIT %s OFFSET %s"
        parametros += (limit, offset)

        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, parametros)
                return cursor.fetchall()

    def obtener_ticket(self, ticket_id: int):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT t.id, t.cliente_id, c.nombre AS cliente, c.plan,
                           t.texto, t.prioridad, t.estado, t.creado,
                           t.primera_respuesta, t.resuelto
                    FROM tickets AS t
                    JOIN clientes AS c ON c.id = t.cliente_id
                    WHERE t.id = %s
                    """,
                    (ticket_id,),
                )
                ticket = cursor.fetchone()
                if ticket is None:
                    return None

                cursor.execute(
                    """
                    SELECT id, tipo, momento
                    FROM eventos
                    WHERE ticket_id = %s
                    ORDER BY momento, id
                    """,
                    (ticket_id,),
                )
                ticket["eventos"] = cursor.fetchall()
                return ticket

    def listar_ejecuciones_ticket(self, ticket_id: int):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT e.id, e.ticket_id, e.creado,
                           e.resultado->'supervision'->>'decision' AS supervision,
                           r.decision AS revision
                    FROM ejecuciones AS e
                    LEFT JOIN revisiones AS r ON r.ejecucion_id = e.id
                    WHERE e.ticket_id = %s
                    ORDER BY e.id DESC
                    """,
                    (ticket_id,),
                )
                return cursor.fetchall()

    def crear_ticket(self, cliente_id: int, texto: str):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT nombre, plan FROM clientes WHERE id = %s",
                    (cliente_id,),
                )
                cliente = cursor.fetchone()
                if cliente is None:
                    return None

                cursor.execute(
                    """
                    INSERT INTO tickets (cliente_id, texto)
                    VALUES (%s, %s)
                    RETURNING id, prioridad, estado, creado
                    """,
                    (cliente_id, texto),
                )
                creado = cursor.fetchone()

        return {
            **creado,
            "cliente_id": cliente_id,
            "cliente": cliente["nombre"],
            "plan": cliente["plan"],
            "texto": texto,
        }

    def guardar_ejecucion(self, ticket_id: int, resultado: dict):
        """Guarda una ejecucion producida por el analisis, nunca por el cliente HTTP."""
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ejecuciones (ticket_id, resultado)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (ticket_id, Jsonb(resultado)),
                )
                return cursor.fetchone()["id"]

    def obtener_ejecucion(self, ejecucion_id: int):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, ticket_id, creado, resultado
                    FROM ejecuciones
                    WHERE id = %s
                    """,
                    (ejecucion_id,),
                )
                ejecucion = cursor.fetchone()
                if ejecucion is None:
                    return None

                cursor.execute(
                    """
                    SELECT id, decision, texto_final, motivo, creado
                    FROM revisiones
                    WHERE ejecucion_id = %s
                    """,
                    (ejecucion_id,),
                )
                ejecucion["revision"] = cursor.fetchone()
                resultado = ejecucion["resultado"]
                if pide_credenciales(
                    resultado.get("borrador", {}),
                    resultado.get("triage", {}).get("faltantes", []),
                ):
                    ejecucion["alerta_seguridad"] = (
                        "Esta ejecucion solicita credenciales; solo puede rechazarse"
                    )
                return ejecucion

    def guardar_revision(
        self, ejecucion_id: int, decision: str, texto_final: str, motivo: str
    ):
        if decision not in ("aprobar", "editar", "rechazar"):
            raise ValueError("Decision invalida")
        motivo = motivo.strip()
        if not motivo:
            raise ValueError("Registrar el motivo de la decision")

        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                # Bloquea esta ejecucion hasta terminar la transaccion. Asi dos
                # revisiones simultaneas no pueden aprobar el mismo analisis.
                cursor.execute(
                    "SELECT resultado FROM ejecuciones WHERE id = %s FOR UPDATE",
                    (ejecucion_id,),
                )
                fila = cursor.fetchone()
                if fila is None:
                    return None

                cursor.execute(
                    "SELECT 1 FROM revisiones WHERE ejecucion_id = %s",
                    (ejecucion_id,),
                )
                if cursor.fetchone() is not None:
                    raise ValueError("Ejecucion ya revisada")

                resultado = fila["resultado"]
                supervision = resultado.get("supervision", {})
                borrador = resultado.get("borrador", {})
                triage = resultado.get("triage", {})
                if supervision.get("decision") not in ("listo", "revisar", "bloquear"):
                    raise ValueError("La ejecucion no tiene supervision valida")
                if pide_credenciales(borrador, triage.get("faltantes", [])) and decision != "rechazar":
                    raise ValueError("La ejecucion solicita credenciales; solo puede rechazarse")
                if supervision["decision"] == "bloquear" and decision != "rechazar":
                    raise ValueError("Un borrador bloqueado solo puede rechazarse")

                if decision == "aprobar":
                    texto = borrador.get("texto", "")
                    if not isinstance(texto, str) or not texto.strip():
                        raise ValueError("El borrador no tiene texto para aprobar")
                    texto_final = texto
                elif decision == "editar":
                    texto_final = texto_final.strip()
                    if not texto_final:
                        raise ValueError("Editar requiere texto final")
                else:
                    texto_final = ""

                cursor.execute(
                    """
                    INSERT INTO revisiones
                        (ejecucion_id, decision, texto_final, motivo)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, ejecucion_id, decision, texto_final, motivo, creado
                    """,
                    (ejecucion_id, decision, texto_final, motivo),
                )
                return cursor.fetchone()

    def obtener_kpis(self):
        with self.conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT estado, COUNT(*) AS cantidad FROM tickets GROUP BY estado"
                )
                cantidades = {fila["estado"]: fila["cantidad"] for fila in cursor.fetchall()}

        abiertos = cantidades.get("abierto", 0)
        resueltos = cantidades.get("resuelto", 0)
        return {
            "tickets": abiertos + resueltos,
            "abiertos": abiertos,
            "resueltos": resueltos,
        }
