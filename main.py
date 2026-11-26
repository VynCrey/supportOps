from typing import Literal
from urllib.error import URLError

from fastapi import FastAPI, HTTPException, Query
from psycopg import OperationalError
from pydantic import BaseModel, Field, ValidationError, field_validator

from analysis import TicketNoEncontrado, analyze
from db import SupportOpsDB


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


class NuevoReclamo(BaseModel):
    cliente_id: int = Field(gt=0)
    texto: str = Field(min_length=10, max_length=4000)
    producto_id: str | None = Field(default=None, max_length=40)
    pedido_id: int | None = Field(default=None, gt=0)


class MensajeCliente(BaseModel):
    cliente_id: int = Field(gt=0)
    texto: str = Field(min_length=10, max_length=4000)


class MensajeSoporte(BaseModel):
    texto: str = Field(min_length=1, max_length=8000)


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
            return analyze(ticket_id, datos)
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
    def crear_reclamo(nuevo: NuevoReclamo):
        texto = nuevo.texto.strip()
        if not 10 <= len(texto) <= 4000:
            raise HTTPException(status_code=422, detail="Describi el reclamo")
        try:
            return datos.crear_reclamo(
                nuevo.cliente_id, texto, nuevo.producto_id, nuevo.pedido_id
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

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
    def enviar_mensaje_cliente(ticket_id: int, nuevo: MensajeCliente):
        try:
            mensaje = datos.enviar_mensaje_cliente(
                ticket_id, nuevo.cliente_id, nuevo.texto
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if mensaje is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return mensaje

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
