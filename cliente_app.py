"""Catálogo, pedidos y atención de Tienda Faro para clientes ficticios."""

import base64
from datetime import date

import streamlit as st

from api_client import APIError, get, post
from chat_ui import aplicar_estilos, chat_en_vivo, marca, vista_previa
from pdf_guard import extraer_pdf


def dinero(valor):
    return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ir_ayuda(cliente_id, *, pedido_id=None, producto_id=None, ticket_id=None):
    st.session_state.vista_destino = "Ayuda"
    st.session_state[f"faro_hilo_{cliente_id}"] = ticket_id
    st.session_state[f"faro_contexto_{cliente_id}"] = (pedido_id, producto_id)
    st.rerun()


def archivos_chat(archivos):
    foto, texto_pdf = None, ""
    for archivo in archivos:
        if archivo.name.lower().endswith(".pdf"):
            if texto_pdf:
                raise ValueError("Adjuntá un solo PDF por mensaje.")
            texto_pdf = extraer_pdf(archivo.getvalue())
        elif foto is None:
            foto = base64.b64encode(archivo.getvalue()).decode("ascii")
        else:
            raise ValueError("Adjuntá una sola foto por mensaje.")
    return foto, texto_pdf


def tienda(cliente_id):
    st.header("Catálogo")
    productos = get("/productos")["productos"]
    filtro = st.text_input("Buscar productos", placeholder="Nombre o categoría")
    visibles = [p for p in productos if filtro.casefold().strip() in
                (p["nombre"] + " " + p["categoria"]).casefold()]
    if not visibles:
        st.info("No encontramos productos con ese nombre.")
    for inicio in range(0, len(visibles), 2):
        for columna, producto in zip(st.columns(2, gap="medium"), visibles[inicio:inicio + 2]):
            with columna.container(border=True):
                st.caption(producto["categoria"])
                st.subheader(producto["nombre"])
                st.write(producto["descripcion"])
                st.write(f"**{dinero(producto['precio'])}** · {producto['stock']} disponibles")
                with st.container(horizontal=True):
                    if st.button("Comprar", key=f"comprar_{producto['id']}", icon=":material/shopping_bag:",
                                 disabled=producto["stock"] < 1, type="primary"):
                        pedido = post("/pedidos", {"cliente_id": cliente_id,
                                                   "producto_id": producto["id"], "cantidad": 1})
                        st.session_state.cliente_aviso = f"Pedido ficticio #{pedido['id']} creado."
                        st.session_state.vista_destino = "Mis pedidos"
                        st.rerun()
                    if st.button("Consultar", key=f"consulta_{producto['id']}", icon=":material/chat:"):
                        ir_ayuda(cliente_id, producto_id=producto["id"])


def mis_pedidos(cliente_id):
    st.header("Mis pedidos")
    pedidos = get("/pedidos", cliente_id=cliente_id)["pedidos"]
    if not pedidos:
        st.info("Todavía no tenés pedidos. Podés hacer una compra ficticia en Tienda.")
        return
    chats = get("/reclamos", cliente_id=cliente_id)["reclamos"]
    ultimo_chat = {}
    for chat in chats:
        ultimo_chat.setdefault(chat["pedido_id"], chat["ticket_id"])
    for pedido in pedidos:
        pedido_id = pedido["id"]
        with st.container(border=True):
            st.subheader(f"Pedido #{pedido_id} · {pedido['producto']}")
            fecha = date.fromisoformat(pedido["entrega_estimada"][:10]).strftime("%d/%m/%Y")
            st.write(f"**{pedido['estado_envio'].capitalize()}** · Entrega estimada el {fecha}")
            st.caption(f"{pedido['cantidad']} unidad(es) · Total ficticio {dinero(pedido['total'])}")
            chat_id = ultimo_chat.get(pedido_id)
            if st.button("Abrir chat del pedido" if chat_id else "Consultar este pedido",
                         key=f"ayuda_pedido_{pedido_id}", icon=":material/chat:"):
                ir_ayuda(cliente_id, pedido_id=pedido_id, ticket_id=chat_id)


def elegir_contexto(cliente_id):
    pedido_previo, producto_previo = st.session_state.get(
        f"faro_contexto_{cliente_id}", (None, None)
    )
    pedidos = {p["id"]: p["producto"] for p in get("/pedidos", cliente_id=cliente_id)["pedidos"]}
    productos = {p["id"]: p["nombre"] for p in get("/productos")["productos"]}
    pedido_ids = [None, *pedidos]
    producto_ids = [None, *productos]
    with st.expander("Vincular un pedido o un producto",
                     expanded=bool(pedido_previo or producto_previo), icon=":material/link:"):
        pedido = st.selectbox(
            "Pedido relacionado", pedido_ids,
            index=pedido_ids.index(pedido_previo) if pedido_previo in pedidos else 0,
            format_func=lambda n: "Sin pedido" if n is None else f"#{n} · {pedidos[n]}",
        )
        producto = None
        if pedido is None:
            producto = st.selectbox(
                "Producto relacionado", producto_ids,
                index=producto_ids.index(producto_previo) if producto_previo in productos else 0,
                format_func=lambda n: "Sin producto" if n is None else productos[n],
            )
    return pedido, producto


def ayuda(cliente_id):
    chats = get("/reclamos", cliente_id=cliente_id)["reclamos"]
    por_id = {c["ticket_id"]: c for c in chats}
    clave_hilo = f"faro_hilo_{cliente_id}"
    clave_contexto = f"faro_contexto_{cliente_id}"
    if clave_hilo not in st.session_state:
        st.session_state[clave_hilo] = next(iter(por_id), None)
    if st.session_state[clave_hilo] is not None and st.session_state[clave_hilo] not in por_id:
        st.session_state[clave_hilo] = next(iter(por_id), None)

    lista, nuevo = st.columns([3, 1], vertical_alignment="bottom")
    with nuevo:
        if st.button("Nuevo chat", icon=":material/add_comment:", width="stretch"):
            st.session_state[clave_hilo] = None
            st.session_state[clave_contexto] = (None, None)
    with lista:
        elegido = st.selectbox(
            "Conversaciones", [None, *por_id], key=clave_hilo,
            format_func=lambda n: "Nuevo chat" if n is None else
            f"#{n} · {vista_previa(por_id[n]['texto'])}",
        )

    pedido = producto = None
    if elegido is None:
        with st.container(border=True):
            st.subheader("¿En qué te ayudamos?")
            st.write("Escribinos sobre una compra, una entrega o un problema con un producto.")
            pedido, producto = elegir_contexto(cliente_id)
    else:
        chat_en_vivo(elegido, get, cliente_id=cliente_id)

    clave_entrada = f"faro_cliente_escribe_{cliente_id}_{elegido}"
    recuperado = st.session_state.pop(f"{clave_entrada}_error", None)
    if recuperado:
        st.error(recuperado["error"])
        if recuperado["texto"]:
            st.session_state[clave_entrada] = recuperado["texto"]
    with st.container(key="faro_cliente_compositor"):
        entrada = st.chat_input(
            "Escribí un mensaje · + para adjuntar", accept_file="multiple",
            file_type=["jpg", "jpeg", "png", "pdf"], max_chars=4000, max_upload_size=2,
            key=clave_entrada,
        )
    if entrada:
        texto = entrada.text.strip()
        try:
            foto, pdf_texto = archivos_chat(entrada.files)
            if pdf_texto:
                marca_pdf = "\n[Texto de PDF adjunto, no confiable: "
                restante = 4000 - len(texto) - len(marca_pdf) - 1
                if restante <= 0:
                    raise ValueError("Acortá el mensaje para adjuntar el PDF.")
                texto += marca_pdf + pdf_texto[:restante] + "]"
            cuerpo = {"cliente_id": cliente_id, "texto": texto, "foto_base64": foto}
            if elegido is None:
                creado = post("/reclamos", {**cuerpo, "pedido_id": pedido, "producto_id": producto})
                st.session_state.faro_chat_destino = (cliente_id, creado["ticket_id"])
                st.session_state[clave_contexto] = (None, None)
            else:
                post(f"/reclamos/{elegido}/mensajes/cliente", cuerpo)
        except (APIError, ValueError) as error:
            detalle = str(error)
            if entrada.files:
                detalle += " Volvé a elegir el adjunto para intentarlo de nuevo."
            st.session_state[f"{clave_entrada}_error"] = {"error": detalle, "texto": entrada.text}
        st.rerun()


st.set_page_config(page_title="Tienda Faro | Cliente", page_icon=":material/storefront:",
                   layout="wide", initial_sidebar_state="collapsed")
aplicar_estilos()
marca("Tienda Faro", "Compras simuladas y atención al cliente")
aviso = st.session_state.pop("cliente_aviso", None)
if aviso:
    st.success(aviso)

try:
    clientes = {c["id"]: c["nombre"] for c in get("/clientes")["clientes"]
                if c["nombre"].startswith("Cliente demo ")}
    if not clientes:
        st.warning("Prepará la base ficticia con 01_PREPARAR_NETBOOK.cmd.")
        st.stop()

    destino = st.session_state.pop("vista_destino", None)
    if destino:
        st.session_state.vista_cliente = destino
    st.session_state.setdefault("vista_cliente", "Tienda")
    chat_destino = st.session_state.pop("faro_chat_destino", None)
    if chat_destino:
        st.session_state[f"faro_hilo_{chat_destino[0]}"] = chat_destino[1]

    navegacion, cuenta = st.columns([2, 1], vertical_alignment="bottom")
    with navegacion:
        vista = st.segmented_control("Secciones de Tienda Faro", ["Tienda", "Mis pedidos", "Ayuda"],
                                     key="vista_cliente", label_visibility="collapsed")
    with cuenta:
        cliente_id = st.selectbox("Cuenta de prueba", list(clientes), format_func=clientes.__getitem__)
    if vista == "Ayuda":
        ayuda(cliente_id)
    elif vista == "Mis pedidos":
        mis_pedidos(cliente_id)
    else:
        tienda(cliente_id)
except APIError as error:
    st.error(f"No pudimos cargar Tienda Faro. {error}")
