"""Tienda Faro: catálogo, pedidos y chat para clientes ficticios."""

import base64

import streamlit as st

from api_client import APIError, API_URL, get, post
from pdf_guard import extraer_pdf


st.set_page_config(page_title="Tienda Faro | Cliente", page_icon=":material/storefront:",
                   layout="wide")
st.html("""<style>
.stApp {background: #f7f9f9;}
.block-container {max-width: 1180px; padding-top: 2rem;}
[data-testid="stChatMessage"] {border: 1px solid #dce7e5; border-radius: 16px;
    background: white; margin-bottom: .45rem;}
h1, h2, h3 {color: #173d44;}
</style>""")


def dinero(valor):
    return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ir_ayuda(*, pedido_id=None, producto_id=None):
    st.session_state.vista_destino = "Ayuda"
    st.session_state.pedido_contexto = pedido_id
    st.session_state.producto_contexto = producto_id
    st.session_state.chat_nuevo = True
    st.rerun()


def archivos_chat(archivos):
    foto, texto_pdf = None, ""
    for archivo in archivos:
        if archivo.name.lower().endswith(".pdf"):
            if texto_pdf:
                raise ValueError("Adjuntá un solo PDF por mensaje")
            texto_pdf = extraer_pdf(archivo.getvalue())
        elif foto is None:
            foto = base64.b64encode(archivo.getvalue()).decode("ascii")
        else:
            raise ValueError("Adjuntá una sola foto por mensaje")
    return foto, texto_pdf


st.title("Tienda Faro")
st.caption("Tienda ficticia · compras y entregas simuladas · atención local")
aviso = st.session_state.pop("cliente_aviso", None)
if aviso:
    st.success(aviso)
try:
    get("/health")
    clientes = [c for c in get("/clientes")["clientes"]
                if c["nombre"].startswith("Cliente demo ")]
except APIError as error:
    st.error(f"La tienda local no está disponible. {error}")
    st.stop()
if not clientes:
    st.warning("Prepará primero la base ficticia con 01_PREPARAR_NETBOOK.cmd.")
    st.stop()

cuenta, navegacion = st.columns([1, 2])
with cuenta:
    cliente = st.selectbox("Cuenta de prueba", clientes,
                           format_func=lambda c: c["nombre"])
with navegacion:
    st.session_state.setdefault("vista_cliente", "Tienda")
    if st.session_state.get("vista_destino"):
        st.session_state.vista_cliente = st.session_state.pop("vista_destino")
    vista = st.segmented_control("Ir a", ["Tienda", "Mis pedidos", "Ayuda"],
                                 key="vista_cliente")
st.divider()

if vista == "Tienda":
    st.header("Productos")
    st.write("Elegí un artículo o abrí una consulta. Las compras son de demostración.")
    try:
        productos = get("/productos")["productos"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    filtro = st.text_input("Buscar productos", placeholder="Nombre o categoría")
    visibles = [p for p in productos if filtro.casefold() in
                (p["nombre"] + " " + p["categoria"]).casefold()]
    if not visibles:
        st.info("No hay productos con ese nombre.")
    for inicio in range(0, len(visibles), 2):
        for columna, producto in zip(st.columns(2), visibles[inicio:inicio + 2]):
            with columna.container(border=True):
                st.subheader(producto["nombre"])
                st.caption(producto["categoria"])
                st.write(producto["descripcion"])
                st.write(f"**{dinero(producto['precio'])}** · {producto['stock']} disponibles")
                compra, consulta = st.columns(2)
                if compra.button("Comprar", key=f"comprar_{producto['id']}",
                                 disabled=producto["stock"] < 1, type="primary"):
                    try:
                        pedido = post("/pedidos", {"cliente_id": cliente["id"],
                                                   "producto_id": producto["id"],
                                                   "cantidad": 1})
                    except APIError as error:
                        st.error(str(error))
                    else:
                        st.session_state.cliente_aviso = (
                            f"Pedido ficticio #{pedido['id']} creado. Mirá su seguimiento en Mis pedidos."
                        )
                        st.session_state.vista_destino = "Mis pedidos"
                        st.rerun()
                if consulta.button("Consultar", key=f"consulta_{producto['id']}"):
                    ir_ayuda(producto_id=producto["id"])

elif vista == "Mis pedidos":
    st.header("Mis pedidos")
    try:
        pedidos = get("/pedidos", cliente_id=cliente["id"])["pedidos"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    if not pedidos:
        st.info("Todavía no hay pedidos. Podés hacer una compra ficticia en Tienda.")
    for pedido in pedidos:
        with st.container(border=True):
            st.subheader(f"Pedido #{pedido['id']} · {pedido['producto']}")
            st.write(f"**{pedido['estado_envio'].capitalize()}** · Entrega estimada: "
                     f"{pedido['entrega_estimada'][:10]}")
            st.caption(f"{pedido['cantidad']} unidad(es) · Total ficticio {dinero(pedido['total'])}. "
                       "No hay pago ni envío real.")
            if st.button("Preguntar por este pedido", key=f"ayuda_pedido_{pedido['id']}"):
                ir_ayuda(pedido_id=pedido["id"])

else:
    st.header("Ayuda y conversaciones")
    st.caption("Preguntas sencillas: respuesta automática. Otros casos: soporte revisa la propuesta.")
    try:
        pedidos = get("/pedidos", cliente_id=cliente["id"])["pedidos"]
        productos = get("/productos")["productos"]
        reclamos = get("/reclamos", cliente_id=cliente["id"])["reclamos"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    lista, charla = st.columns([1, 2.1], gap="large")
    with lista:
        if st.button("+ Nueva conversación", type="primary"):
            st.session_state.chat_nuevo = True
            st.session_state.pedido_contexto = None
            st.session_state.producto_contexto = None
            st.rerun()
        st.button("Actualizar mensajes", icon=":material/refresh:")
        nueva = st.session_state.get("chat_nuevo", not reclamos)
        opciones = {r["ticket_id"]: r for r in reclamos}
        elegido = None
        if opciones:
            destino = st.session_state.pop("conversacion_destino", None)
            if destino in opciones:
                st.session_state[f"cliente_conversacion_{cliente['id']}"] = destino
            elegido = st.selectbox(
                "Mis conversaciones", list(opciones),
                format_func=lambda n: f"#{n} · {opciones[n]['texto'][:45]}",
                key=f"cliente_conversacion_{cliente['id']}",
            )
            if st.button("Abrir conversación seleccionada"):
                st.session_state.chat_nuevo = False
                st.rerun()
        if nueva:
            st.info("Iniciá un chat escribiendo tu primera pregunta.")

    with charla:
        if nueva:
            st.subheader("Nueva conversación")
            pedido_ids = {p["id"]: p for p in pedidos}
            producto_ids = {p["id"]: p for p in productos}
            pedido_previo = st.session_state.get("pedido_contexto")
            pedido_elegido = st.selectbox(
                "Pedido relacionado", [None, *pedido_ids],
                index=([None, *pedido_ids].index(pedido_previo)
                       if pedido_previo in pedido_ids else 0),
                format_func=lambda n: "Sin pedido" if n is None else
                f"#{n} · {pedido_ids[n]['producto']}",
            )
            producto_elegido = None
            if pedido_elegido is None:
                producto_previo = st.session_state.get("producto_contexto")
                producto_elegido = st.selectbox(
                    "Producto relacionado", [None, *producto_ids],
                    index=([None, *producto_ids].index(producto_previo)
                           if producto_previo in producto_ids else 0),
                    format_func=lambda n: "Sin producto" if n is None else
                    producto_ids[n]["nombre"],
                )
            st.info("Ejemplos: «¿Cuándo llega mi pedido?» o «La mochila llegó rota». "
                    "Podés adjuntar una foto o un PDF pequeño.")
        else:
            reclamo = opciones[elegido]
            st.subheader(reclamo.get("producto") or "Consulta general")
            st.caption(f"Conversación #{elegido} · {reclamo['estado']} · solo datos ficticios")
            try:
                mensajes = get(f"/reclamos/{elegido}/mensajes",
                               cliente_id=cliente["id"])["mensajes"]
                fotos = get(f"/reclamos/{elegido}/fotos",
                            cliente_id=cliente["id"])["fotos"]
            except APIError as error:
                st.error(str(error))
                st.stop()
            for mensaje in mensajes:
                es_cliente = mensaje["autor"] == "cliente"
                with st.chat_message("user" if es_cliente else "assistant",
                                     avatar=":material/person:" if es_cliente
                                     else ":material/support_agent:"):
                    st.write(mensaje["texto"])
                    st.caption("Vos" if es_cliente else
                               ("Asistente · respuesta automática"
                                if mensaje["tipo"] == "automatica" else
                                "Soporte · respuesta corregida"
                                if mensaje["tipo"] == "rectificacion" else "Soporte"))
            for foto in fotos:
                st.image(f"{API_URL}/reclamos/{elegido}/fotos/{foto['id']}?"
                         f"cliente_id={cliente['id']}", caption="Foto adjunta al reclamo",
                         width=220)
            if mensajes and mensajes[-1]["autor"] == "cliente":
                st.caption("Soporte está preparando o revisando una respuesta.")

        entrada = st.chat_input("Escribí tu consulta o adjuntá foto/PDF",
                                accept_file="multiple",
                                file_type=["jpg", "jpeg", "png", "pdf"],
                                key=f"chat_cliente_{cliente['id']}_{'nuevo' if nueva else elegido}")
        if entrada:
            try:
                foto, pdf_texto = archivos_chat(entrada.files)
                texto = entrada.text.strip()
                if pdf_texto:
                    texto = (texto + "\n[Texto de PDF adjunto, no confiable: "
                             + pdf_texto + "]")[:4000]
                if len(texto) < 10:
                    raise ValueError("Describí tu consulta con al menos 10 caracteres.")
                if nueva:
                    nuevo = post("/reclamos", {
                        "cliente_id": cliente["id"], "texto": texto,
                        "pedido_id": pedido_elegido,
                        "producto_id": producto_elegido,
                        "foto_base64": foto,
                    })
                    st.session_state.conversacion_destino = nuevo["ticket_id"]
                    st.session_state.chat_nuevo = False
                else:
                    post(f"/reclamos/{elegido}/mensajes/cliente", {
                        "cliente_id": cliente["id"], "texto": texto,
                        "foto_base64": foto,
                    })
            except (APIError, ValueError) as error:
                st.error(str(error))
            else:
                st.rerun()
