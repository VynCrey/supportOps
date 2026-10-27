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

    return app