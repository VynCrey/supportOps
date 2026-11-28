"""Presentación y actualización del chat en las dos vistas de Tienda Faro."""

from datetime import datetime
from html import escape

import streamlit as st

from api_client import APIError, API_URL


_ESTILOS = """
<style>
.stApp { background: #f1f5f3; }
.block-container { max-width: 1310px; padding: 3.1rem clamp(1rem, 3vw, 2.6rem) 1.5rem; }
.faro-marca { display: flex; align-items: center; gap: .8rem; padding-bottom: .15rem; }
.faro-marca-chip { display: inline-grid; place-items: center; width: 2.6rem; height: 2.6rem;
    border-radius: .75rem; background: #164a47; color: white; font-size: 1.35rem; font-weight: 700; }
.faro-marca h1 { margin: 0; padding: 0; font-size: clamp(1.35rem, 2.8vw, 1.9rem); line-height: 1.2; }
.faro-marca p { margin: .15rem 0 0; font-size: .84rem; color: #4c6966; }
.faro-cabecera { display: flex; justify-content: space-between; align-items: center;
    gap: .6rem; flex-wrap: wrap; padding: .8rem 1rem; border-radius: .85rem;
    background: #164a47; color: white; }
.faro-cabecera h2 { margin: 0; padding: 0; font-size: 1.06rem; line-height: 1.3; color: white; }
.faro-cabecera p { margin: .2rem 0 0; font-size: .8rem; color: #c6e4db; }
.faro-cabecera span { white-space: nowrap; border: 1px solid #a9d1c4; background: #215d58;
    border-radius: 999px; padding: .2rem .65rem; font-size: .76rem; color: white; }
div[data-testid="stVerticalBlock"][class*="st-key-faro_mensajes_"],
div[data-testid="stLayoutWrapper"]:has(> div[data-testid="stVerticalBlock"][class*="st-key-faro_mensajes_"]) {
    background: #e8f0eb; border-radius: .85rem;
}
.faro-conversacion { display: flex; flex-direction: column; gap: .6rem; padding: .12rem; }
.faro-mensaje { width: fit-content; max-width: min(86%, 43rem); align-self: flex-start;
    border: 1px solid #cddfd7; background: #fff; padding: .55rem .75rem;
    border-radius: .3rem 1rem 1rem 1rem; box-shadow: 0 1px 2px #17382c0e; }
.faro-mensaje-propio { align-self: flex-end; background: #d7eee3; border-color: #b8dbcb;
    border-radius: 1rem .3rem 1rem 1rem; }
.faro-meta { display: flex; align-items: baseline; justify-content: space-between; gap: .9rem;
    margin-bottom: .22rem; font-size: .74rem; color: #315854; }
.faro-meta time { color: #4e6663; font-variant-numeric: tabular-nums; }
.faro-texto { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.45; color: #20343a; }
.faro-mensaje img, .faro-fotos img { display: block; width: min(13rem, 100%);
    max-height: 13rem; object-fit: contain; border-radius: .45rem; margin-top: .4rem; }
.faro-mensaje details { margin-top: .35rem; color: #245451; font-size: .84rem; }
.faro-mensaje summary { cursor: pointer; }
.faro-mensaje details .faro-texto { margin-top: .4rem; }
.st-key-faro_bandeja_lista [data-testid="stButton"] button { min-height: 3.1rem;
    justify-content: flex-start; text-align: left; padding: .45rem .65rem; }
.st-key-faro_bandeja_lista [data-testid="stButton"] button p { overflow-wrap: anywhere; }
.st-key-faro_propuesta { background: white; border-radius: .8rem; }
@media (max-width: 760px) {
    .st-key-faro_bandeja_lista,
    [data-testid="stLayoutWrapper"]:has(> .st-key-faro_bandeja_lista) {
        max-height: 9rem; min-height: 0;
    }
    .faro-mensaje { max-width: 94%; }
}
</style>
"""


def aplicar_estilos():
    st.html(_ESTILOS)


def marca(titulo: str, descripcion: str):
    st.html(
        f'<div class="faro-marca"><span class="faro-marca-chip" aria-hidden="true">F</span>'
        f"<div><h1>{escape(titulo)}</h1><p>{escape(descripcion)}</p></div></div>"
    )


def vista_previa(texto: str, limite: int = 56) -> str:
    texto, _, pdf = texto.partition("[Texto de PDF adjunto, no confiable: ")
    breve = " ".join(texto.split()) or ("PDF adjunto" if pdf else "")
    return breve if len(breve) <= limite else breve[:limite - 1] + "…"


def _hora(valor: str | None) -> str:
    if not valor:
        return ""
    return datetime.fromisoformat(valor).astimezone().strftime("%H:%M")


def _imagen(ticket_id: int, foto_id: int, cliente_id: int | None) -> str:
    url = f"{API_URL}/reclamos/{ticket_id}/fotos/{foto_id}"
    if cliente_id is not None:
        url += f"?cliente_id={cliente_id}"
    url = escape(url, quote=True)
    return (f'<a href="{url}" target="_blank" rel="noopener" aria-label="Ampliar foto del reclamo">'
            f'<img src="{url}" alt="Foto adjunta al reclamo" loading="lazy"></a>')


def _mensaje_html(mensaje: dict, chat: dict, fotos: list[dict], cliente_id: int | None) -> str:
    escrito_por_cliente = mensaje["autor"] == "cliente"
    propio = escrito_por_cliente == (cliente_id is not None) and mensaje["tipo"] != "automatica"
    tipo = mensaje["tipo"]
    if escrito_por_cliente:
        autor = "Vos" if cliente_id is not None else chat["cliente"]
    elif tipo == "automatica":
        autor = "Asistente de Faro"
    elif tipo == "rectificacion":
        autor = "Soporte · corrección"
    else:
        autor = "Soporte" if cliente_id is not None else "Vos · Soporte"
    texto, separador, pdf = mensaje["texto"].partition("[Texto de PDF adjunto, no confiable: ")
    html_pdf = (f'<details><summary>Texto del PDF adjunto</summary><div class="faro-texto">'
                f'{escape(pdf.removesuffix("]"))}</div></details>') if separador else ""
    adjuntos = "".join(_imagen(chat["ticket_id"], f["id"], cliente_id) for f in fotos)
    clase = "faro-mensaje faro-mensaje-propio" if propio else "faro-mensaje"
    return (
        f'<article class="{clase}"><div class="faro-meta"><strong>{escape(autor)}</strong>'
        f'<time>{_hora(mensaje.get("creado"))}</time></div>'
        f'<div class="faro-texto">{escape(texto.strip())}</div>{html_pdf}{adjuntos}</article>'
    )


@st.fragment(run_every="3s")
def chat_en_vivo(ticket_id: int, leer, *, cliente_id: int | None = None):
    """Actualiza únicamente el historial, dejando el cuadro de escritura intacto."""
    identidad = (cliente_id, ticket_id)
    opciones = {"cliente_id": cliente_id} if cliente_id is not None else {}
    try:
        chat = leer(f"/reclamos/{ticket_id}/chat", **opciones)
    except APIError:
        identidad_previa, chat = st.session_state.get("faro_ultimo_chat", (None, None))
        st.caption("El chat perdió la conexión. Se actualizará cuando vuelva la API.")
        if identidad_previa != identidad or chat is None:
            return
    else:
        st.session_state.faro_ultimo_chat = (identidad, chat)

    mensajes = chat["mensajes"]
    espera_soporte = bool(mensajes and mensajes[-1]["autor"] == "cliente")
    if espera_soporte:
        estado = "Esperando a soporte" if cliente_id is not None else "Por responder"
    elif chat["estado"] == "resuelto":
        estado = "Respondida"
    else:
        estado = "Esperamos tu mensaje" if cliente_id is not None else "Esperando al cliente"
    asunto = chat.get("producto") or "Consulta general"
    referencia = f"Chat #{ticket_id} · {asunto}"
    if chat.get("pedido_id"):
        referencia += f" · Pedido #{chat['pedido_id']}"
    titulo = "Chat con soporte" if cliente_id is not None else chat["cliente"]
    st.html(
        f'<header class="faro-cabecera"><div><h2>{escape(titulo)}</h2>'
        f'<p>{escape(referencia)}</p></div><span>{estado}</span></header>'
    )

    fotos_por_mensaje = {}
    for foto in chat["fotos"]:
        fotos_por_mensaje.setdefault(foto.get("mensaje_id"), []).append(foto)
    with st.container(height=340, border=True, autoscroll=True,
                      key=f"faro_mensajes_{cliente_id or 'soporte'}_{ticket_id}"):
        if not mensajes:
            st.caption("Todavía no hay mensajes.")
            return
        contenido = "".join(
            _mensaje_html(m, chat, fotos_por_mensaje.pop(m["id"], []), cliente_id)
            for m in mensajes
        )
        fotos_anteriores = "".join(
            _imagen(ticket_id, foto["id"], cliente_id)
            for fotos in fotos_por_mensaje.values() for foto in fotos
        )
        if fotos_anteriores:
            contenido += f'<details class="faro-fotos"><summary>Fotos anteriores</summary>{fotos_anteriores}</details>'
        st.html(f'<section class="faro-conversacion" aria-label="Mensajes">{contenido}</section>')
