import base64
import binascii
from datetime import datetime, timezone
from typing import Literal
from urllib.error import URLError

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from psycopg import OperationalError
from pydantic import BaseModel, Field, ValidationError, field_validator

from analysis import TicketNoEncontrado, analyze
from db import SupportOpsDB
from foto_guard import preparar_foto
from tienda_respuestas import respuesta_simple


Plan = Literal["Basic", "Pro", "Enterprise"]


class NuevoTicket(BaseModel):
    cliente_id: int = Field(gt=0)
    texto: str = Field(min_length=10, max_length=4000)


class NuevaRevision(BaseModel):
    decision: Literal["aprobar", "editar", "rechazar"]
    texto_final: str = Field(default="", max_length=8000)
    motivo: str = Field(min_length=1, max_length=1000)

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Registrar el motivo de la decision")
        if valor.casefold() == "string":
            raise ValueError("Reemplazá el texto de ejemplo por un motivo real")
        return valor


class NuevoPedido(BaseModel):
    cliente_id: int = Field(gt=0)
    producto_id: str = Field(min_length=1, max_length=40)
    cantidad: int = Field(ge=1, le=10)


class MensajeCliente(BaseModel):
    cliente_id: int = Field(gt=0)
    texto: str = Field(default="", max_length=4000)
    foto_base64: str | None = Field(default=None, max_length=3_000_000)


class NuevoReclamo(MensajeCliente):
    producto_id: str | None = Field(default=None, max_length=40)
    pedido_id: int | None = Field(default=None, gt=0)


class MensajeSoporte(BaseModel):
    texto: str = Field(min_length=1, max_length=8000)


class FotoNueva(BaseModel):
    cliente_id: int = Field(gt=0)
    contenido_base64: str = Field(min_length=1, max_length=3_000_000)


class RectificacionMensaje(BaseModel):
    texto: str = Field(min_length=1, max_length=8000)
    motivo: str = Field(min_length=1, max_length=1000)


class NuevaCorreccion(BaseModel):
    decision: Literal["editar", "rechazar"]
    texto_final: str = Field(default="", max_length=8000)
    motivo: str = Field(min_length=1, max_length=1000)
    operador: str = Field(default="Operador demo", min_length=1, max_length=100)

    @field_validator("motivo")
    @classmethod
    def motivo_real(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor or valor.casefold() == "string":
            raise ValueError("Escribi el motivo de la correccion")
        return valor


def crear_app(clave_db: str) -> FastAPI:
    app = FastAPI(title="SupportOps", version="0.1.0")
    datos = SupportOpsDB(clave_db)
    inicio_api = datetime.now(timezone.utc)

    def preparar_propuesta(ticket_id: int, mensaje_id: int):
        try:
            conversacion = datos.contexto_conversacion(ticket_id)
            if conversacion["ultimo_mensaje_id"] != mensaje_id:
                return
            resultado = analyze(ticket_id, datos, conversacion=conversacion)
        except Exception:
            datos.terminar_borrador_pendiente(
                mensaje_id, None, "No pudimos preparar una propuesta. Podés reintentar o responder por el chat."
            )
        else:
            datos.terminar_borrador_pendiente(mensaje_id, resultado["ejecucion_id"])

    def atender_mensaje(ticket_id: int, mensaje_id: int, tareas: BackgroundTasks) -> dict:
        conversacion = datos.contexto_conversacion(ticket_id)
        if conversacion["ultimo_mensaje_id"] != mensaje_id:
            return {"atencion": "sin_cambio"}
        texto = conversacion["ultimo_texto_cliente"] or ""
        contexto = datos.contexto_reclamo(ticket_id) or {}
        producto = None
        if contexto.get("producto_id"):
            producto = {"nombre": contexto["producto"],
                        "precio": contexto["precio"], "stock": contexto["stock"]}
        pedido = datos.pedido_del_reclamo(ticket_id)
        fotos = datos.fotos_reclamo(ticket_id) or []
        respuesta = respuesta_simple(
            texto, pedido=pedido, producto=producto, tiene_foto=bool(fotos),
            anteriores=conversacion["mensajes"][:-1],
        )
        if respuesta:
            publicado = datos.publicar_automatica(
                ticket_id, mensaje_id, respuesta.texto, respuesta.resuelve
            )
            return ({"atencion": "automatica", "mensaje": publicado}
                    if publicado else {"atencion": "sin_cambio"})
        if datos.registrar_borrador_pendiente(ticket_id, mensaje_id, inicio_api):
            tareas.add_task(preparar_propuesta, ticket_id, mensaje_id)
        return {"atencion": "soporte", "propuesta": "preparando"}

    def decodificar_foto(contenido_base64: str | None):
        if not contenido_base64:
            return None
        try:
            contenido = base64.b64decode(contenido_base64, validate=True)
            return preparar_foto(contenido)
        except (binascii.Error, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    def leer_entrada(nuevo: MensajeCliente):
        foto = decodificar_foto(nuevo.foto_base64)
        texto = nuevo.texto.strip()
        if not texto:
            if foto is None:
                raise HTTPException(status_code=422, detail="Escribí un mensaje o adjuntá una foto.")
            texto = "Adjunté una foto del producto."
        return texto, foto

    @app.get("/health")
    def health():
        try:
            datos.comprobar()
        except OperationalError:
            raise HTTPException(status_code=503, detail="PostgreSQL no disponible")
        return {"estado": "ok", "base": "conectada"}

    @app.get("/clientes")
    def listar_clientes():
        return {"clientes": datos.listar_clientes()}

    @app.get("/tickets")
    def listar_tickets(plan: Plan | None = None,
                       limit: int = Query(default=50, ge=1, le=200),
                       offset: int = Query(default=0, ge=0)):
        tickets = datos.listar_tickets(plan, limit, offset)
        return {
            "cantidad": datos.contar_tickets(plan),
            "tickets": tickets,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/tickets/{ticket_id}")
    def obtener_ticket(ticket_id: int):
        if ticket_id <= 0:
            raise HTTPException(status_code=422, detail="El ID debe ser mayor que cero")
        ticket = datos.obtener_ticket(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return ticket

    @app.get("/tickets/{ticket_id}/ejecuciones")
    def listar_ejecuciones_ticket(ticket_id: int):
        if ticket_id <= 0:
            raise HTTPException(status_code=422, detail="El ID debe ser mayor que cero")
        if datos.obtener_ticket(ticket_id) is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return {"ejecuciones": datos.listar_ejecuciones_ticket(ticket_id)}

    @app.post("/tickets/{ticket_id}/analizar")
    def analizar_ticket(ticket_id: int):
        if ticket_id <= 0:
            raise HTTPException(status_code=422, detail="El ID debe ser mayor que cero")
        try:
            resultado = analyze(ticket_id, datos)
            if resultado.get("mensaje_cliente_id"):
                datos.terminar_borrador_pendiente(
                    resultado["mensaje_cliente_id"], resultado["ejecucion_id"]
                )
            return resultado
        except TicketNoEncontrado as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (URLError, TimeoutError, ConnectionError, OSError) as error:
            raise HTTPException(
                status_code=503, detail="Modelo o base de conocimiento no disponible"
            ) from error
        except (ValueError, ValidationError, TypeError, KeyError) as error:
            raise HTTPException(status_code=502, detail="Salida del analisis invalida") from error

    @app.post("/tickets", status_code=201)
    def crear_ticket(nuevo: NuevoTicket):
        texto = nuevo.texto.strip()
        if not 10 <= len(texto) <= 4000:
            raise HTTPException(
                status_code=422,
                detail="El texto debe tener entre 10 y 4000 caracteres",
            )
        ticket = datos.crear_ticket(nuevo.cliente_id, texto)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return ticket

    @app.get("/kpis")
    def obtener_kpis():
        return datos.obtener_kpis()

    @app.get("/ejecuciones/{ejecucion_id}")
    def obtener_ejecucion(ejecucion_id: int):
        if ejecucion_id <= 0:
            raise HTTPException(status_code=422, detail="El ID debe ser mayor que cero")
        ejecucion = datos.obtener_ejecucion(ejecucion_id)
        if ejecucion is None:
            raise HTTPException(status_code=404, detail="Ejecucion no encontrada")
        return ejecucion

    @app.post("/ejecuciones/{ejecucion_id}/revision")
    def guardar_revision(ejecucion_id: int, nueva: NuevaRevision):
        if ejecucion_id <= 0:
            raise HTTPException(status_code=422, detail="El ID debe ser mayor que cero")
        try:
            revision = datos.guardar_revision(
                ejecucion_id,
                nueva.decision,
                nueva.texto_final,
                nueva.motivo,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if revision is None:
            raise HTTPException(status_code=404, detail="Ejecucion no encontrada")
        return revision

    @app.get("/productos")
    def listar_productos():
        return {"productos": datos.listar_productos()}

    @app.get("/pedidos")
    def listar_pedidos(cliente_id: int | None = Query(default=None, gt=0)):
        return {"pedidos": datos.listar_pedidos(cliente_id)}

    @app.post("/pedidos", status_code=201)
    def crear_pedido(nuevo: NuevoPedido):
        try:
            return datos.crear_pedido(
                nuevo.cliente_id, nuevo.producto_id, nuevo.cantidad
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/reclamos")
    def listar_reclamos(cliente_id: int | None = Query(default=None, gt=0)):
        return {"reclamos": datos.listar_reclamos(cliente_id)}

    @app.post("/reclamos", status_code=201)
    def crear_reclamo(nuevo: NuevoReclamo, tareas: BackgroundTasks):
        texto, foto = leer_entrada(nuevo)
        try:
            reclamo = datos.crear_reclamo(
                nuevo.cliente_id, texto, nuevo.producto_id, nuevo.pedido_id, foto=foto,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {**reclamo, **atender_mensaje(reclamo["ticket_id"], reclamo["mensaje_cliente_id"], tareas)}

    @app.get("/reclamos/{ticket_id}/chat")
    def leer_chat(ticket_id: int, cliente_id: int | None = Query(default=None, gt=0)):
        chat = datos.leer_chat(ticket_id, cliente_id)
        if chat is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return chat

    @app.get("/reclamos/{ticket_id}/mensajes")
    def listar_mensajes_reclamo(
        ticket_id: int, cliente_id: int | None = Query(default=None, gt=0)
    ):
        mensajes = datos.listar_mensajes_reclamo(ticket_id, cliente_id)
        if mensajes is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return {"ticket_id": ticket_id, "mensajes": mensajes}

    @app.get("/reclamos/{ticket_id}/mensajes/historial")
    def historial_mensajes_reclamo(ticket_id: int):
        mensajes = datos.historial_mensajes_reclamo(ticket_id)
        if mensajes is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return {"ticket_id": ticket_id, "mensajes": mensajes}

    @app.post("/reclamos/{ticket_id}/mensajes/cliente", status_code=201)
    def enviar_mensaje_cliente(ticket_id: int, nuevo: MensajeCliente,
                               tareas: BackgroundTasks):
        texto, foto = leer_entrada(nuevo)
        try:
            mensaje = datos.enviar_mensaje_cliente(
                ticket_id, nuevo.cliente_id, texto, foto=foto,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if mensaje is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return {**mensaje, **atender_mensaje(ticket_id, mensaje["id"], tareas)}

    @app.get("/reclamos/{ticket_id}/propuesta")
    def estado_propuesta(ticket_id: int):
        propuesta = datos.estado_borrador(ticket_id, inicio_api)
        if propuesta is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return propuesta

    @app.post("/reclamos/{ticket_id}/propuesta", status_code=202)
    def reintentar_propuesta(ticket_id: int, tareas: BackgroundTasks):
        if not datos.es_reclamo(ticket_id):
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        mensaje_id = datos.contexto_conversacion(ticket_id)["mensaje_cliente_id"]
        if mensaje_id is None or not datos.registrar_borrador_pendiente(ticket_id, mensaje_id, inicio_api):
            raise HTTPException(status_code=409, detail="Ya hay una propuesta o el mensaje fue respondido.")
        tareas.add_task(preparar_propuesta, ticket_id, mensaje_id)
        return {"estado": "preparando"}

    @app.get("/reclamos/{ticket_id}/fotos")
    def listar_fotos(ticket_id: int, cliente_id: int | None = Query(default=None, gt=0)):
        fotos = datos.fotos_reclamo(ticket_id, cliente_id)
        if fotos is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return {"fotos": fotos}

    @app.get("/reclamos/{ticket_id}/fotos/{foto_id}")
    def obtener_foto(ticket_id: int, foto_id: int,
                     cliente_id: int | None = Query(default=None, gt=0)):
        foto = datos.obtener_foto_reclamo(ticket_id, foto_id, cliente_id)
        if foto is None:
            raise HTTPException(status_code=404, detail="Foto no encontrada")
        return Response(content=bytes(foto["datos"]), media_type=foto["mime"])

    @app.post("/reclamos/{ticket_id}/fotos", status_code=201)
    def agregar_foto(ticket_id: int, nueva: FotoNueva, tareas: BackgroundTasks):
        mime, contenido = decodificar_foto(nueva.contenido_base64)
        foto = datos.guardar_foto_reclamo(ticket_id, nueva.cliente_id, mime, contenido)
        if foto is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return {**foto, **atender_mensaje(ticket_id, foto["mensaje_id"], tareas)}

    @app.post("/reclamos/{ticket_id}/mensajes/soporte", status_code=201)
    def enviar_mensaje_soporte(ticket_id: int, nuevo: MensajeSoporte):
        try:
            mensaje = datos.enviar_mensaje_soporte(ticket_id, nuevo.texto)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if mensaje is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return mensaje

    @app.post("/reclamos/{ticket_id}/mensajes/{mensaje_id}/rectificar", status_code=201)
    def rectificar_mensaje_soporte(
        ticket_id: int, mensaje_id: int, nuevo: RectificacionMensaje
    ):
        try:
            mensaje = datos.rectificar_mensaje_soporte(
                ticket_id, mensaje_id, nuevo.texto, nuevo.motivo
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if mensaje is None:
            raise HTTPException(status_code=404, detail="Mensaje no encontrado")
        return mensaje

    @app.get("/reclamos/{ticket_id}/respuesta")
    def respuesta_reclamo(ticket_id: int, cliente_id: int = Query(gt=0)):
        ticket = datos.obtener_ticket(ticket_id)
        if (ticket is None or ticket["cliente_id"] != cliente_id
                or not datos.es_reclamo(ticket_id)):
            raise HTTPException(status_code=404, detail="Reclamo no encontrado")
        if hasattr(datos, "listar_mensajes_reclamo"):
            mensajes = datos.listar_mensajes_reclamo(ticket_id, cliente_id) or []
            if mensajes and mensajes[-1]["autor"] == "soporte":
                ultimo = mensajes[-1]
                return {
                    "ticket_id": ticket_id, "estado": "respondido",
                    "texto": ultimo["texto"], "version": 2 if ultimo["tipo"] == "rectificacion" else 1,
                    "corregida": ultimo["tipo"] == "rectificacion",
                }
            return {"ticket_id": ticket_id, "estado": "pendiente", "texto": ""}
        for ejecucion in datos.listar_ejecuciones_ticket(ticket_id):
            historial = datos.historial_revision(ejecucion["id"])
            if historial is not None:
                vigente = historial["vigente"]
                return {
                    "ticket_id": ticket_id,
                    "estado": "sin_respuesta" if vigente["decision"] == "rechazar" else "respondido",
                    "texto": vigente["texto_final"] if vigente["decision"] != "rechazar" else "",
                    "version": 1 + len(historial["correcciones"]),
                    "corregida": bool(historial["correcciones"]),
                }
        return {"ticket_id": ticket_id, "estado": "pendiente", "texto": ""}

    @app.get("/ejecuciones/{ejecucion_id}/historial")
    def historial_revision(ejecucion_id: int):
        historial = datos.historial_revision(ejecucion_id)
        if historial is None:
            raise HTTPException(status_code=404, detail="Revision no encontrada")
        return historial

    @app.post("/ejecuciones/{ejecucion_id}/correcciones", status_code=201)
    def guardar_correccion(ejecucion_id: int, nueva: NuevaCorreccion):
        try:
            correccion = datos.guardar_correccion(
                ejecucion_id, nueva.decision, nueva.texto_final,
                nueva.motivo, nueva.operador,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if correccion is None:
            raise HTTPException(status_code=404, detail="Revision no encontrada")
        return correccion

    return app
