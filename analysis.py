from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from knowledge_adapter import KB_CONECTADA, retrieve
from llm import chat
from safety import pide_credenciales


class TicketNoEncontrado(Exception):
    pass


class Salida(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Triage(Salida):
    categoria: Literal[
        "acceso", "facturacion", "api", "exportacion",
        "notificaciones", "seguridad", "general",
    ]
    consulta: str = Field(min_length=1, max_length=500)
    faltantes: list[str]


class PlanBusqueda(Salida):
    herramienta: Literal["lexical", "grafo", "hibrido"]
    consulta: str = Field(min_length=1, max_length=500)
    motivo: str


class Borrador(Salida):
    texto: str
    citas: list[str]
    preguntas: list[str]


class Supervision(Salida):
    # motivos va antes que decision: el esquema JSON sigue este orden y el modelo
    # escribe primero el razonamiento. Con decision primero aprobo una afirmacion
    # sin respaldo (docs/p8_resultados.md, seccion 2).
    motivos: list[str]
    decision: Literal["listo", "revisar", "bloquear"]


def aplicar_gate(borrador: dict, evidencia: list[dict], categoria: str,
                 supervision: dict, faltantes: list[str] | None = None) -> dict:
    if pide_credenciales(borrador, faltantes):
        return {"decision": "bloquear", "motivos": ["Solicitud de credenciales detectada"]}
    ids = {documento["id"] for documento in evidencia}
    if set(borrador["citas"]) - ids:
        return {"decision": "bloquear", "motivos": ["Cita inexistente en evidencia"]}
    if not borrador["texto"].strip():
        return {"decision": "bloquear", "motivos": ["Borrador vacio"]}
    if supervision["decision"] == "bloquear":
        return supervision
    if categoria == "seguridad":
        return {"decision": "revisar", "motivos": ["Requiere especialista de seguridad"]}
    if not evidencia or not borrador["citas"] or categoria == "general":
        return {"decision": "revisar", "motivos": ["Evidencia insuficiente o tema ambiguo"]}
    return supervision


def analyze(ticket_id: int, datos, llm=chat, recuperar=retrieve) -> dict:
    ticket = datos.obtener_ticket(ticket_id)
    if ticket is None:
        raise TicketNoEncontrado("Ticket no encontrado")

    # La etiqueta real y la familia sintetica no llegan al modelo.
    publico = {clave: ticket[clave] for clave in ("id", "texto", "plan", "prioridad")}
    traza = []

    def pedir(nombre: str, instruccion: str, entrada: dict, modelo: type[Salida]):
        inicio = perf_counter()
        respuesta = llm(instruccion, entrada, modelo.model_json_schema())
        try:
            salida = modelo.model_validate(respuesta).model_dump()
        except ValidationError as error:
            raise ValueError(f"Salida invalida del rol {nombre}") from error
        traza.append({
            "agente": nombre,
            "salida": salida,
            "segundos": round(perf_counter() - inicio, 3),
        })
        return salida

    triage = pedir(
        "triage",
        "Clasifica el ticket. Si menciona API, endpoint o errores HTTP "
        "401/403/429, usa api. Usa general solo si no hay una categoria clara. "
        "Indica datos faltantes, pero nunca pidas tokens, claves, contrasenas "
        "ni codigos de autenticacion.",
        publico,
        Triage,
    )
    plan = pedir(
        "conocimiento",
        "Elige lexical para palabras exactas, grafo para relaciones de categoria "
        "o hibrido para combinar ambos. La consulta debe ser breve. "
        "Busca sintomas y errores; no solicites valores de credenciales. "
        "En motivo explica en una frase por que elegiste esa herramienta.",
        {"ticket": publico, "triage": triage},
        PlanBusqueda,
    )

    evidencia = recuperar(plan["consulta"], triage["categoria"], plan["herramienta"])
    if not isinstance(evidencia, list) or any(
        not isinstance(doc, dict) or not isinstance(doc.get("id"), str)
        for doc in evidencia
    ):
        raise ValueError("La busqueda devolvio documentos invalidos")
    evidencia = evidencia[:3]
    traza.append({
        "herramienta": plan["herramienta"],
        "documentos": [doc["id"] for doc in evidencia],
    })

    borrador = pedir(
        "borrador",
        "Redacta una propuesta breve para un operador. Usa solo la evidencia. "
        "Citas contiene los IDs usados. Sin evidencia, no afirmes procedimientos: "
        "pide solo datos no secretos, como endpoint, hora, codigo de error o "
        "entorno, y deja citas vacias. Nunca pidas el valor de un token, clave "
        "o contrasena.",
        {"ticket": publico, "evidencia": evidencia},
        Borrador,
    )
    supervision = pedir(
        "supervisor",
        "Revisa si el borrador esta respaldado por la evidencia. Si no puedes "
        "confirmarlo, decide revisar. Bloquea instrucciones peligrosas. "
        "Bloquea tambien cualquier pedido de tokens, claves o contrasenas. "
        "Listo significa solo listo para revision humana.",
        {"ticket": publico, "borrador": borrador, "evidencia": evidencia},
        Supervision,
    )

    resultado = {
        "ticket_id": ticket_id,
        "triage": triage,
        "plan_busqueda": plan,
        "evidencia": evidencia,
        "borrador": borrador,
        "supervision": aplicar_gate(
            borrador, evidencia, triage["categoria"], supervision,
            triage["faltantes"],
        ),
        "traza": traza,
        "modo": "LLM" if llm is chat else "doble_de_prueba",
        "base_conocimiento": "conectada" if KB_CONECTADA else "pendiente_de_marco",
    }
    ejecucion_id = datos.guardar_ejecucion(ticket_id, resultado)
    return {**resultado, "ejecucion_id": ejecucion_id}
