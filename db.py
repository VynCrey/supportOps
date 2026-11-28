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
    def _registrar_estado_ticket(cursor, ticket_id: int, publicado: bool | None,
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
        elif publicado is False:
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

                cursor.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE",
                               (fila["ticket_id"],))

                cursor.execute(
                    "SELECT 1 FROM reclamos WHERE ticket_id = %s",
                    (fila["ticket_id"],),
                )
                es_reclamo = cursor.fetchone() is not None
                corresponde_al_ultimo = True
                if es_reclamo:
                    ultimo_mensaje = self._ultimo_mensaje_vigente(cursor, fila["ticket_id"])
                    corresponde_al_ultimo = bool(
                        ultimo_mensaje and resultado.get("ultimo_mensaje_id") == ultimo_mensaje["id"]
                    )
                    if not corresponde_al_ultimo and decision != "rechazar":
                        raise ValueError(
                            "La conversación cambió después del análisis. Volvé a analizar antes de responder"
                        )

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
                if es_reclamo and decision != "rechazar":
                    cursor.execute(
                        """
                        INSERT INTO mensajes_reclamo
                            (ticket_id, autor, texto, ejecucion_id, tipo)
                        VALUES (%s, 'soporte', %s, %s, 'revision')
                        """,
                        (fila["ticket_id"], texto_final, ejecucion_id),
                    )
                self._registrar_estado_ticket(
                    cursor, fila["ticket_id"], (decision != "rechazar") if corresponde_al_ultimo else None,
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
                   p.cantidad * p.precio_unitario AS total, p.estado, p.creado,
                   p.entrega_estimada,
                   CASE WHEN now() >= p.entrega_estimada THEN 'entregado'
                        WHEN now() >= p.creado + INTERVAL '1 day' THEN 'en camino'
                        ELSE 'en preparación' END AS estado_envio
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
                RETURNING id, estado, creado, entrega_estimada
                """,
                (cliente_id, producto_id, cantidad, producto["precio"]),
            )
            fila = cursor.fetchone()
            return {
                **fila, "cliente_id": cliente_id, "cliente": cliente["nombre"],
                "producto_id": producto_id, "producto": producto["nombre"],
                "cantidad": cantidad, "precio_unitario": producto["precio"],
                "total": cantidad * producto["precio"],
                "estado_envio": "en preparación",
            }

    def crear_reclamo(self, cliente_id: int, texto: str,
                      producto_id: str | None = None,
                      pedido_id: int | None = None, *,
                      foto: tuple[str, bytes] | None = None):
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
            cursor.execute(
                """
                INSERT INTO mensajes_reclamo (ticket_id, autor, texto, tipo)
                VALUES (%s, 'cliente', %s, 'inicio')
                RETURNING id
                """,
                (ticket["id"], texto),
            )
            mensaje_id = cursor.fetchone()["id"]
            if foto:
                self._guardar_foto_mensaje(cursor, ticket["id"], cliente_id, mensaje_id, foto)
            return {
                **ticket, "reclamo_id": reclamo["id"], "ticket_id": ticket["id"],
                "cliente_id": cliente_id, "cliente": cliente["nombre"],
                "plan": cliente["plan"], "texto": texto,
                "producto_id": producto_id, "pedido_id": pedido_id,
                "mensaje_cliente_id": mensaje_id,
            }

    def listar_reclamos(self, cliente_id: int | None = None):
        consulta = """
            SELECT r.id, r.ticket_id, r.pedido_id, r.producto_id,
                   pr.nombre AS producto, t.cliente_id, c.nombre AS cliente,
                   t.texto, t.estado, t.creado,
                   ultimo.texto AS ultimo_texto, ultimo.creado AS ultima_actividad,
                   COALESCE(ultimo.autor = 'cliente', FALSE) AS necesita_soporte
            FROM reclamos AS r
            JOIN tickets AS t ON t.id = r.ticket_id
            JOIN clientes AS c ON c.id = t.cliente_id
            LEFT JOIN productos AS pr ON pr.id = r.producto_id
            LEFT JOIN LATERAL (
                SELECT m.id, m.texto, m.creado, m.autor
                FROM mensajes_reclamo AS m
                WHERE m.ticket_id = t.id AND m.vigente
                ORDER BY COALESCE(m.orden_id, m.id) DESC, m.id DESC LIMIT 1
            ) AS ultimo ON TRUE
        """
        parametros = ()
        if cliente_id is not None:
            consulta += " WHERE t.cliente_id = %s"
            parametros = (cliente_id,)
        consulta += " ORDER BY ultimo.id DESC NULLS LAST, r.id DESC LIMIT 100"
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
                       r.pedido_id, p.estado AS estado_pedido, p.cantidad,
                       p.entrega_estimada,
                       CASE WHEN now() >= p.entrega_estimada THEN 'entregado'
                            WHEN now() >= p.creado + INTERVAL '1 day' THEN 'en camino'
                            ELSE 'en preparación' END AS estado_envio
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

    def pedido_del_reclamo(self, ticket_id: int):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """SELECT p.id, pr.nombre AS producto, p.entrega_estimada,
                          CASE WHEN now() >= p.entrega_estimada THEN 'entregado'
                               WHEN now() >= p.creado + INTERVAL '1 day' THEN 'en camino'
                               ELSE 'en preparación' END AS estado_envio
                   FROM reclamos r JOIN tickets t ON t.id = r.ticket_id
                   JOIN pedidos p ON p.id = r.pedido_id AND p.cliente_id = t.cliente_id
                   JOIN productos pr ON pr.id = p.producto_id
                   WHERE r.ticket_id = %s""", (ticket_id,)
            )
            return cursor.fetchone()

    def fotos_reclamo(self, ticket_id: int, cliente_id: int | None = None):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT t.cliente_id FROM reclamos r JOIN tickets t "
                           "ON t.id = r.ticket_id WHERE r.ticket_id = %s", (ticket_id,))
            fila = cursor.fetchone()
            if fila is None or (cliente_id is not None and fila["cliente_id"] != cliente_id):
                return None
            return self._fotos_visibles(cursor, ticket_id)

    @staticmethod
    def _fotos_visibles(cursor, ticket_id: int):
        cursor.execute(
            "SELECT id, mime, creado, mensaje_id FROM fotos_reclamo "
            "WHERE ticket_id = %s ORDER BY id", (ticket_id,),
        )
        return cursor.fetchall()

    @staticmethod
    def _guardar_foto_mensaje(cursor, ticket_id: int, cliente_id: int,
                             mensaje_id: int, foto: tuple[str, bytes]):
        mime, contenido = foto
        cursor.execute(
            """
            INSERT INTO fotos_reclamo (ticket_id, cliente_id, mime, datos, mensaje_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, ticket_id, mime, creado, mensaje_id
            """,
            (ticket_id, cliente_id, mime, contenido, mensaje_id),
        )
        return cursor.fetchone()

    def guardar_foto_reclamo(self, ticket_id: int, cliente_id: int, mime: str,
                             contenido: bytes):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT 1 FROM reclamos r JOIN tickets t ON t.id = r.ticket_id "
                           "WHERE r.ticket_id = %s AND t.cliente_id = %s FOR UPDATE OF t",
                           (ticket_id, cliente_id))
            if cursor.fetchone() is None:
                return None
            cursor.execute("INSERT INTO mensajes_reclamo (ticket_id, autor, texto) "
                           "VALUES (%s, 'cliente', 'Adjunté una foto del producto.') RETURNING id",
                           (ticket_id,))
            foto = self._guardar_foto_mensaje(
                cursor, ticket_id, cliente_id, cursor.fetchone()["id"], (mime, contenido)
            )
            self._registrar_estado_ticket(cursor, ticket_id, False, "foto_cliente")
            return foto

    def obtener_foto_reclamo(self, ticket_id: int, foto_id: int,
                             cliente_id: int | None = None):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT f.mime, f.datos FROM fotos_reclamo f "
                           "JOIN tickets t ON t.id = f.ticket_id "
                           "WHERE f.ticket_id = %s AND f.id = %s "
                           "AND (%s::bigint IS NULL OR t.cliente_id = %s)",
                           (ticket_id, foto_id, cliente_id, cliente_id))
            return cursor.fetchone()

    def publicar_automatica(self, ticket_id: int, mensaje_id: int, texto: str,
                            resuelto: bool):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
            ultimo = self._ultimo_mensaje_vigente(cursor, ticket_id)
            if not ultimo or ultimo["id"] != mensaje_id:
                return None
            cursor.execute("INSERT INTO mensajes_reclamo (ticket_id, autor, texto, tipo) "
                           "VALUES (%s, 'soporte', %s, 'automatica') "
                           "RETURNING id, ticket_id, autor, texto, creado, tipo",
                           (ticket_id, texto))
            mensaje = cursor.fetchone()
            self._registrar_estado_ticket(cursor, ticket_id, resuelto, "respuesta_automatica")
            return mensaje

    def registrar_borrador_pendiente(self, ticket_id: int, mensaje_id: int, inicio_api):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
            cursor.execute(
                """
                INSERT INTO borradores_pendientes (ticket_id, mensaje_id, estado)
                SELECT %s, id, 'preparando'
                FROM (
                    SELECT id, autor FROM mensajes_reclamo WHERE ticket_id = %s AND vigente
                    ORDER BY COALESCE(orden_id, id) DESC, id DESC LIMIT 1
                ) AS ultimo
                WHERE id = %s AND autor = 'cliente'
                ON CONFLICT (mensaje_id) DO UPDATE
                    SET estado = 'preparando', ejecucion_id = NULL, detalle = '', actualizado = now()
                WHERE borradores_pendientes.estado = 'error'
                   OR (borradores_pendientes.estado = 'preparando'
                       AND (borradores_pendientes.actualizado < %s
                            OR borradores_pendientes.actualizado < now() - INTERVAL '15 minutes'))
                   OR EXISTS (
                       SELECT 1 FROM revisiones
                       WHERE ejecucion_id = borradores_pendientes.ejecucion_id
                         AND decision = 'rechazar'
                   )
                RETURNING mensaje_id
                """,
                (ticket_id, ticket_id, mensaje_id, inicio_api),
            )
            return cursor.fetchone() is not None

    def terminar_borrador_pendiente(self, mensaje_id: int, ejecucion_id: int | None,
                                    detalle: str = ""):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("UPDATE borradores_pendientes SET estado = %s, "
                           "ejecucion_id = %s, detalle = %s, actualizado = now() "
                           "WHERE mensaje_id = %s",
                           ("listo" if ejecucion_id else "error", ejecucion_id,
                            detalle[:200], mensaje_id))

    def estado_borrador(self, ticket_id: int, inicio_api):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT CASE WHEN m.autor = 'soporte' THEN 'respondido'
                            WHEN v.decision = 'rechazar' THEN 'rechazado'
                            WHEN b.estado = 'preparando'
                                AND (b.actualizado < %s
                                    OR b.actualizado < now() - INTERVAL '15 minutes') THEN 'error'
                            ELSE COALESCE(b.estado, 'sin propuesta') END AS estado,
                       CASE WHEN m.autor = 'cliente' THEN b.ejecucion_id END AS ejecucion_id,
                       NULLIF(b.detalle, '') AS detalle
                FROM mensajes_reclamo m
                LEFT JOIN borradores_pendientes b ON b.mensaje_id = m.id
                LEFT JOIN revisiones v ON v.ejecucion_id = b.ejecucion_id
                WHERE m.ticket_id = %s AND m.vigente
                ORDER BY COALESCE(m.orden_id, m.id) DESC, m.id DESC LIMIT 1
                """,
                (inicio_api, ticket_id),
            )
            return cursor.fetchone()

    def listar_mensajes_reclamo(self, ticket_id: int, cliente_id: int | None = None):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.cliente_id FROM reclamos AS r
                JOIN tickets AS t ON t.id = r.ticket_id
                WHERE r.ticket_id = %s
                """,
                (ticket_id,),
            )
            reclamo = cursor.fetchone()
            if reclamo is None or (cliente_id is not None and
                                  reclamo["cliente_id"] != cliente_id):
                return None
            return self._mensajes_visibles(cursor, ticket_id)

    @staticmethod
    def _ultimo_mensaje_vigente(cursor, ticket_id: int):
        cursor.execute(
            "SELECT id FROM mensajes_reclamo WHERE ticket_id = %s AND vigente "
            "ORDER BY COALESCE(orden_id, id) DESC, id DESC LIMIT 1",
            (ticket_id,),
        )
        return cursor.fetchone()

    @staticmethod
    def _mensajes_visibles(cursor, ticket_id: int):
        cursor.execute(
            """
            SELECT id, ticket_id, autor, texto, creado, tipo
            FROM mensajes_reclamo WHERE ticket_id = %s AND vigente
            ORDER BY COALESCE(orden_id, id), id
            """,
            (ticket_id,),
        )
        return cursor.fetchall()

    def leer_chat(self, ticket_id: int, cliente_id: int | None = None):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            # La vista de cliente solo recibe la conversación de la cuenta elegida.
            cursor.execute(
                """
                SELECT t.estado, c.nombre AS cliente, r.pedido_id, pr.nombre AS producto
                FROM reclamos r JOIN tickets t ON t.id = r.ticket_id
                JOIN clientes c ON c.id = t.cliente_id
                LEFT JOIN productos pr ON pr.id = r.producto_id
                WHERE r.ticket_id = %s AND (%s::bigint IS NULL OR t.cliente_id = %s)
                """,
                (ticket_id, cliente_id, cliente_id),
            )
            chat = cursor.fetchone()
            if chat is None:
                return None
            return {**chat, "ticket_id": ticket_id,
                    "mensajes": self._mensajes_visibles(cursor, ticket_id),
                    "fotos": self._fotos_visibles(cursor, ticket_id)}

    def historial_mensajes_reclamo(self, ticket_id: int):
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT 1 FROM reclamos WHERE ticket_id = %s", (ticket_id,))
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                """
                SELECT id, autor, texto, tipo, vigente, rectifica_id, motivo, creado, ejecucion_id
                FROM mensajes_reclamo WHERE ticket_id = %s ORDER BY id
                """,
                (ticket_id,),
            )
            return cursor.fetchall()

    def contexto_conversacion(self, ticket_id: int):
        """Solo mensajes publicados de este reclamo, sin propuestas internas."""
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                WITH recientes AS (
                    SELECT id, autor, texto, tipo, COALESCE(orden_id, id) AS posicion
                    FROM mensajes_reclamo WHERE ticket_id = %s AND vigente
                    ORDER BY posicion DESC, id DESC LIMIT 8
                ), ultimo_cliente AS (
                    SELECT id, texto FROM mensajes_reclamo
                    WHERE ticket_id = %s AND vigente AND autor = 'cliente'
                    ORDER BY id DESC LIMIT 1
                )
                SELECT COALESCE((SELECT jsonb_agg(to_jsonb(m) ORDER BY m.posicion, m.id)
                                 FROM recientes m),
                                '[]'::jsonb) AS mensajes,
                       (SELECT id FROM recientes ORDER BY posicion DESC, id DESC LIMIT 1)
                           AS ultimo_mensaje_id,
                       (SELECT id FROM ultimo_cliente) AS mensaje_cliente_id,
                       (SELECT texto FROM ultimo_cliente) AS ultimo_texto_cliente
                """,
                (ticket_id, ticket_id),
            )
            return cursor.fetchone()

    def rectificar_mensaje_soporte(self, ticket_id: int, mensaje_id: int,
                                  texto: str, motivo: str):
        texto, motivo = texto.strip(), motivo.strip()
        if not 1 <= len(texto) <= 8000 or not motivo or motivo.casefold() == "string":
            raise ValueError("Escribí una respuesta corregida y el motivo real")
        if pide_credenciales({"texto": texto}):
            raise ValueError("La respuesta solicita credenciales y no puede enviarse")
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
            cursor.execute(
                """
                SELECT m.id, m.ejecucion_id, COALESCE(m.orden_id, m.id) AS posicion
                FROM mensajes_reclamo AS m
                WHERE m.id = %s AND m.ticket_id = %s AND m.autor = 'soporte'
                  AND m.vigente FOR UPDATE
                """,
                (mensaje_id, ticket_id),
            )
            original = cursor.fetchone()
            if original is None:
                return None
            if original["ejecucion_id"] is not None:
                raise ValueError("Corregí esta propuesta desde Análisis y revisión")
            cursor.execute(
                "UPDATE mensajes_reclamo SET vigente = FALSE WHERE id = %s",
                (mensaje_id,),
            )
            cursor.execute(
                """
                INSERT INTO mensajes_reclamo
                    (ticket_id, autor, texto, tipo, rectifica_id, motivo, orden_id)
                VALUES (%s, 'soporte', %s, 'rectificacion', %s, %s, %s)
                RETURNING id, ticket_id, autor, texto, creado, tipo
                """,
                (ticket_id, texto, mensaje_id, motivo, original["posicion"]),
            )
            mensaje = cursor.fetchone()
            self._registrar_estado_ticket(cursor, ticket_id, None, "rectificacion_soporte")
            return mensaje

    def enviar_mensaje_cliente(self, ticket_id: int, cliente_id: int, texto: str, *,
                               foto: tuple[str, bytes] | None = None):
        texto = texto.strip()
        if not 1 <= len(texto) <= 4000:
            raise ValueError("Escribí un mensaje de hasta 4000 caracteres")
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.id FROM tickets AS t JOIN reclamos AS r ON r.ticket_id = t.id
                WHERE t.id = %s AND t.cliente_id = %s FOR UPDATE OF t
                """,
                (ticket_id, cliente_id),
            )
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                """
                INSERT INTO mensajes_reclamo (ticket_id, autor, texto)
                VALUES (%s, 'cliente', %s)
                RETURNING id, ticket_id, autor, texto, creado, tipo
                """,
                (ticket_id, texto),
            )
            mensaje = cursor.fetchone()
            if foto:
                self._guardar_foto_mensaje(cursor, ticket_id, cliente_id, mensaje["id"], foto)
            self._registrar_estado_ticket(cursor, ticket_id, False, "mensaje_cliente")
            return mensaje

    def enviar_mensaje_soporte(self, ticket_id: int, texto: str):
        texto = texto.strip()
        if not 1 <= len(texto) <= 8000:
            raise ValueError("Escribí una respuesta antes de enviarla")
        if pide_credenciales({"texto": texto}):
            raise ValueError("La respuesta solicita credenciales y no puede enviarse")
        with self.conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT t.id FROM tickets AS t JOIN reclamos AS r ON r.ticket_id = t.id
                WHERE t.id = %s FOR UPDATE OF t
                """,
                (ticket_id,),
            )
            if cursor.fetchone() is None:
                return None
            cursor.execute(
                """
                INSERT INTO mensajes_reclamo (ticket_id, autor, texto)
                VALUES (%s, 'soporte', %s)
                RETURNING id, ticket_id, autor, texto, creado, tipo
                """,
                (ticket_id, texto),
            )
            mensaje = cursor.fetchone()
            self._registrar_estado_ticket(cursor, ticket_id, True, "mensaje_soporte")
            return mensaje

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
            ticket_id = original["ticket_id"]
            cursor.execute("SELECT id FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
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
            ultimo = self._ultimo_mensaje_vigente(cursor, ticket_id)
            cursor.execute(
                "UPDATE mensajes_reclamo SET vigente = FALSE "
                "WHERE ejecucion_id = %s AND vigente "
                "RETURNING id, COALESCE(orden_id, id) AS posicion",
                (ejecucion_id,),
            )
            anterior = cursor.fetchone()
            cursor.execute(
                "SELECT 1 FROM reclamos WHERE ticket_id = %s",
                (ticket_id,),
            )
            es_reclamo = cursor.fetchone() is not None
            if es_reclamo and decision == "editar":
                cursor.execute(
                    """
                    INSERT INTO mensajes_reclamo
                        (ticket_id, autor, texto, ejecucion_id, tipo, orden_id, rectifica_id, motivo)
                    VALUES (%s, 'soporte', %s, %s, 'rectificacion', %s, %s, %s)
                    """,
                    (ticket_id, texto_final, ejecucion_id,
                     anterior["posicion"] if anterior else None,
                     anterior["id"] if anterior else None, motivo.strip()),
                )
            publicado = decision == "editar"
            if es_reclamo and anterior and ultimo and anterior["id"] != ultimo["id"]:
                publicado = None
            self._registrar_estado_ticket(
                cursor, ticket_id, publicado,
                "correccion_" + decision,
            )
            return correccion
