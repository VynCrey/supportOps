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

    @staticmethod
    def _registrar_estado_ticket(cursor, ticket_id: int, publicado: bool,
                                 tipo_evento: str):
        if publicado:
            cursor.execute(
                """
                UPDATE tickets SET estado = 'resuelto',
                    primera_respuesta = COALESCE(primera_respuesta, now()),
                    resuelto = now()
                WHERE id = %s
                """,
                (ticket_id,),
            )
        else:
            cursor.execute(
                "UPDATE tickets SET estado = 'abierto', resuelto = NULL WHERE id = %s",
                (ticket_id,),
            )
        cursor.execute(
            "INSERT INTO eventos (ticket_id, tipo, momento) VALUES (%s, %s, now())",
            (ticket_id, tipo_evento),
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
                    "SELECT ticket_id, resultado FROM ejecuciones WHERE id = %s FOR UPDATE",
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
                    if pide_credenciales({"texto": texto_final}):
                        raise ValueError("La respuesta editada solicita credenciales")
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
                revision = cursor.fetchone()
                self._registrar_estado_ticket(
                    cursor, fila["ticket_id"], decision != "rechazar",
                    "revision_" + decision,
                )
                return revision

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

    def listar_productos(self):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre, categoria, descripcion, precio, stock "
                "FROM productos ORDER BY categoria, nombre"
            )
            return cursor.fetchall()

    def listar_pedidos(self, cliente_id: int | None = None):
        consulta = """
            SELECT p.id, p.cliente_id, c.nombre AS cliente, p.producto_id,
                   pr.nombre AS producto, p.cantidad, p.precio_unitario,
                   p.cantidad * p.precio_unitario AS total, p.estado, p.creado
            FROM pedidos AS p
            JOIN clientes AS c ON c.id = p.cliente_id
            JOIN productos AS pr ON pr.id = p.producto_id
        """
        parametros = ()
        if cliente_id is not None:
            consulta += " WHERE p.cliente_id = %s"
            parametros = (cliente_id,)
        consulta += " ORDER BY p.id DESC LIMIT 100"
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()

    def crear_pedido(self, cliente_id: int, producto_id: str, cantidad: int):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT nombre FROM clientes WHERE id = %s", (cliente_id,))
            cliente = cursor.fetchone()
            if cliente is None:
                raise LookupError("Cliente ficticio no encontrado")
            cursor.execute(
                "SELECT id, nombre, precio, stock FROM productos WHERE id = %s FOR UPDATE",
                (producto_id,),
            )
            producto = cursor.fetchone()
            if producto is None:
                raise LookupError("Producto no encontrado")
            if producto["stock"] < cantidad:
                raise ValueError("No hay stock ficticio suficiente")
            cursor.execute(
                "UPDATE productos SET stock = stock - %s WHERE id = %s",
                (cantidad, producto_id),
            )
            cursor.execute(
                """
                INSERT INTO pedidos (cliente_id, producto_id, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
                RETURNING id, estado, creado
                """,
                (cliente_id, producto_id, cantidad, producto["precio"]),
            )
            fila = cursor.fetchone()
            return {
                **fila, "cliente_id": cliente_id, "cliente": cliente["nombre"],
                "producto_id": producto_id, "producto": producto["nombre"],
                "cantidad": cantidad, "precio_unitario": producto["precio"],
                "total": cantidad * producto["precio"],
            }

    def crear_reclamo(self, cliente_id: int, texto: str,
                      producto_id: str | None = None,
                      pedido_id: int | None = None):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                "SELECT nombre, plan FROM clientes WHERE id = %s", (cliente_id,)
            )
            cliente = cursor.fetchone()
            if cliente is None:
                raise LookupError("Cliente ficticio no encontrado")
            if producto_id is not None:
                cursor.execute("SELECT nombre FROM productos WHERE id = %s", (producto_id,))
                if cursor.fetchone() is None:
                    raise LookupError("Producto no encontrado")
            if pedido_id is not None:
                cursor.execute(
                    "SELECT producto_id FROM pedidos WHERE id = %s AND cliente_id = %s",
                    (pedido_id, cliente_id),
                )
                pedido = cursor.fetchone()
                if pedido is None:
                    raise LookupError("Pedido no encontrado para este cliente")
                if producto_id is not None and pedido["producto_id"] != producto_id:
                    raise ValueError("El producto no corresponde al pedido")
                producto_id = pedido["producto_id"]
            cursor.execute(
                "INSERT INTO tickets (cliente_id, texto) VALUES (%s, %s) "
                "RETURNING id, prioridad, estado, creado",
                (cliente_id, texto),
            )
            ticket = cursor.fetchone()
            cursor.execute(
                "INSERT INTO reclamos (ticket_id, pedido_id, producto_id) "
                "VALUES (%s, %s, %s) RETURNING id",
                (ticket["id"], pedido_id, producto_id),
            )
            reclamo = cursor.fetchone()
            return {
                **ticket, "reclamo_id": reclamo["id"], "ticket_id": ticket["id"],
                "cliente_id": cliente_id, "cliente": cliente["nombre"],
                "plan": cliente["plan"], "texto": texto,
                "producto_id": producto_id, "pedido_id": pedido_id,
            }

    def listar_reclamos(self, cliente_id: int | None = None):
        consulta = """
            SELECT r.id, r.ticket_id, r.pedido_id, r.producto_id,
                   pr.nombre AS producto, t.cliente_id, c.nombre AS cliente,
                   t.texto, t.estado, t.creado
            FROM reclamos AS r
            JOIN tickets AS t ON t.id = r.ticket_id
            JOIN clientes AS c ON c.id = t.cliente_id
            LEFT JOIN productos AS pr ON pr.id = r.producto_id
        """
        parametros = ()
        if cliente_id is not None:
            consulta += " WHERE t.cliente_id = %s"
            parametros = (cliente_id,)
        consulta += " ORDER BY r.id DESC LIMIT 100"
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)
            return cursor.fetchall()

    def contexto_reclamo(self, ticket_id: int):
        """Datos de un único producto/pedido ficticio, sin datos de otros clientes."""
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.producto_id, pr.nombre AS producto,
                       pr.descripcion, pr.precio, pr.stock,
                       r.pedido_id, p.estado AS estado_pedido, p.cantidad
                FROM reclamos AS r
                LEFT JOIN productos AS pr ON pr.id = r.producto_id
                LEFT JOIN pedidos AS p ON p.id = r.pedido_id
                WHERE r.ticket_id = %s
                """,
                (ticket_id,),
            )
            return cursor.fetchone()

    def es_reclamo(self, ticket_id: int) -> bool:
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT 1 FROM reclamos WHERE ticket_id = %s", (ticket_id,))
            return cursor.fetchone() is not None

    def historial_revision(self, ejecucion_id: int):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.ejecucion_id, r.decision, r.texto_final,
                       r.motivo, r.creado
                FROM revisiones AS r WHERE r.ejecucion_id = %s
                """,
                (ejecucion_id,),
            )
            original = cursor.fetchone()
            if original is None:
                return None
            cursor.execute(
                """
                SELECT id, revision_id, decision, texto_final, motivo,
                       operador, creado
                FROM correcciones WHERE revision_id = %s ORDER BY id
                """,
                (original["id"],),
            )
            correcciones = cursor.fetchall()
            return {
                "original": original, "correcciones": correcciones,
                "vigente": correcciones[-1] if correcciones else original,
            }

    def guardar_correccion(self, ejecucion_id: int, decision: str,
                           texto_final: str, motivo: str, operador: str):
        if decision not in ("editar", "rechazar"):
            raise ValueError("La correccion debe editar o retirar la respuesta")
        if not motivo.strip():
            raise ValueError("La correccion necesita un motivo")
        texto_final = texto_final.strip() if decision == "editar" else ""
        if decision == "editar" and not texto_final:
            raise ValueError("Escribi la respuesta corregida")
        if decision == "editar" and pide_credenciales({"texto": texto_final}):
            raise ValueError("La correccion solicita credenciales")
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, e.ticket_id, e.resultado
                FROM revisiones AS r
                JOIN ejecuciones AS e ON e.id = r.ejecucion_id
                WHERE r.ejecucion_id = %s FOR UPDATE OF r
                """,
                (ejecucion_id,),
            )
            original = cursor.fetchone()
            if original is None:
                return None
            resultado = original["resultado"]
            if decision == "editar" and (
                resultado.get("supervision", {}).get("decision") == "bloquear"
                or pide_credenciales(
                    resultado.get("borrador", {}),
                    resultado.get("triage", {}).get("faltantes", []),
                )
            ):
                raise ValueError("Un analisis bloqueado no puede publicarse")
            cursor.execute(
                """
                INSERT INTO correcciones
                    (revision_id, decision, texto_final, motivo, operador)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, revision_id, decision, texto_final, motivo,
                          operador, creado
                """,
                (original["id"], decision, texto_final, motivo.strip(), operador.strip()),
            )
            correccion = cursor.fetchone()
            self._registrar_estado_ticket(
                cursor, original["ticket_id"], decision == "editar",
                "correccion_" + decision,
            )
            return correccion
