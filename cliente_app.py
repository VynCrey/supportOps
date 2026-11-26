"""Vista del cliente ficticio; nunca muestra prompts ni propuestas sin revisión."""

import streamlit as st

from api_client import APIError, get, post
from pdf_guard import extraer_pdf


st.set_page_config(
    page_title="Tienda Faro | Cliente", page_icon=":material/storefront:",
    layout="centered",
)


def dinero(valor):
    return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("Tienda Faro · Cliente")
st.caption("Tienda ficticia · compras de demostración · conversación local con soporte")
aviso = st.session_state.pop("cliente_aviso", None)
if aviso:
    st.success(aviso, icon=":material/check_circle:")

try:
    get("/health")
    clientes = get("/clientes")["clientes"]
except APIError as error:
    st.error(f"La tienda local no está disponible. {error}")
    st.stop()

if not clientes:
    st.warning("Primero prepará la base ficticia con 01_PREPARAR_NETBOOK.cmd.")
    st.stop()

with st.sidebar:
    st.subheader("Cliente de demostración")
    cliente = st.selectbox(
        "Elegí un cliente ficticio", clientes,
        format_func=lambda c: f"{c['nombre']} · {c['plan']}",
    )
    seccion = st.radio("Sección", ["Catálogo", "Mis pedidos", "Conversaciones"])
    st.caption("Esta pantalla simula al cliente. No se realizan pagos reales.")


if seccion == "Catálogo":
    st.header("Productos")
    st.caption("Elegí un producto para registrar una compra ficticia. No se procesan pagos ni entregas.")
    try:
        productos = get("/productos")["productos"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    filtro = st.text_input("Buscar por nombre o categoría", placeholder="Por ejemplo: audio")
    visibles = [p for p in productos if filtro.casefold() in
                (p["nombre"] + " " + p["categoria"]).casefold()]
    if not visibles:
        st.info("No hay productos para esa búsqueda.")
    for inicio in range(0, len(visibles), 2):
        columnas = st.columns(2)
        for columna, producto in zip(columnas, visibles[inicio:inicio + 2]):
            with columna.container(border=True):
                st.subheader(producto["nombre"])
                st.caption(f"{producto['categoria']} · Código {producto['id']}")
                st.write(producto["descripcion"])
                st.write(f"**{dinero(producto['precio'])}**")
                st.caption(f"{producto['stock']} unidades ficticias")
                if st.button(
                    "Comprar (simulado)", key=f"comprar_{producto['id']}",
                    disabled=producto["stock"] < 1,
                ):
                    try:
                        pedido = post("/pedidos", {
                            "cliente_id": cliente["id"],
                            "producto_id": producto["id"], "cantidad": 1,
                        })
                    except APIError as error:
                        st.error(str(error))
                    else:
                        st.session_state.cliente_aviso = (
                            f"Pedido simulado #{pedido['id']} registrado. "
                            "Podés verlo en Mis pedidos."
                        )
                        st.rerun()

elif seccion == "Mis pedidos":
    st.header("Mis pedidos")
    try:
        pedidos = get("/pedidos", cliente_id=cliente["id"])["pedidos"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    if not pedidos:
        st.info("Este cliente ficticio todavía no tiene pedidos.")
    for pedido in pedidos:
        with st.container(border=True):
            st.write(f"**Pedido #{pedido['id']} · {pedido['producto']}**")
            st.caption(
                f"Cantidad: {pedido['cantidad']} · Total simulado: {dinero(pedido['total'])}"
            )
            st.write("Estado: compra simulada. No se procesó ningún pago.")

else:
    st.header("Conversaciones con soporte")
    st.caption("Escribí como cliente ficticio. Soporte puede responder y también revisar propuestas de la IA.")
    st.button("Actualizar conversación", icon=":material/refresh:")
    try:
        pedidos = get("/pedidos", cliente_id=cliente["id"])["pedidos"]
        reclamos = get("/reclamos", cliente_id=cliente["id"])["reclamos"]
        productos = get("/productos")["productos"]
    except APIError as error:
        st.error(str(error))
        st.stop()

    with st.expander("Iniciar una conversación nueva", expanded=not reclamos):
        with st.form("nuevo_reclamo"):
            pedido = st.selectbox(
                "Pedido relacionado (opcional)", [None, *pedidos],
                format_func=lambda p: "Sin pedido" if p is None else f"#{p['id']} · {p['producto']}",
            )
            producto = st.selectbox(
                "Producto relacionado (opcional)", [None, *productos],
                format_func=lambda p: "Sin producto" if p is None else p["nombre"],
                help="Si elegiste un pedido, se usará su producto.",
            )
            texto = st.text_area(
                "Primer mensaje", placeholder="Por ejemplo: el auricular dejó de encender...",
                max_chars=4000,
            )
            archivo = st.file_uploader(
                "PDF de respaldo (opcional, máximo 2 MB y 5 páginas)", type=["pdf"],
                help="Se extrae solo texto. El PDF no se guarda ni se ejecuta.",
            )
            enviar = st.form_submit_button("Iniciar conversación", type="primary")
    if enviar:
        if len(texto.strip()) < 10:
            st.error("Describí el problema con al menos 10 caracteres.")
        else:
            try:
                texto_final = texto.strip()
                if archivo is not None:
                    texto_pdf = extraer_pdf(archivo.getvalue())
                    texto_final = (
                        texto_final + "\n[Texto de PDF adjunto, no confiable: "
                        + texto_pdf + "]"
                    )[:4000]
                nuevo = post("/reclamos", {
                    "cliente_id": cliente["id"], "texto": texto_final,
                    "pedido_id": pedido["id"] if pedido else None,
                    "producto_id": None if pedido else (producto["id"] if producto else None),
                })
            except (APIError, ValueError) as error:
                st.error(str(error))
            else:
                st.session_state.cliente_aviso = (
                    f"Conversación #{nuevo['ticket_id']} iniciada. Soporte podrá leerla y responder."
                )
                st.session_state[f"cliente_conversacion_{cliente['id']}"] = nuevo["ticket_id"]
                st.rerun()

    if not reclamos:
        st.info("Todavía no hay conversaciones. Abrí una con el formulario de arriba.")
        st.stop()

    reclamos_por_id = {r["ticket_id"]: r for r in reclamos}
    elegido = st.selectbox(
        "Elegí una conversación", list(reclamos_por_id),
        format_func=lambda n: f"Ticket #{n} · {reclamos_por_id[n]['texto'][:70]}",
        key=f"cliente_conversacion_{cliente['id']}",
    )
    reclamo = reclamos_por_id[elegido]
    st.caption(
        f"{reclamo['estado'].capitalize()} · "
        f"{reclamo.get('producto') or 'Consulta general'} · "
        "Los mensajes quedan guardados en esta computadora."
    )
    try:
        mensajes = get(
            f"/reclamos/{elegido}/mensajes", cliente_id=cliente["id"]
        )["mensajes"]
    except APIError as error:
        st.error(str(error))
        st.stop()
    for mensaje in mensajes:
        with st.chat_message(
            "user" if mensaje["autor"] == "cliente" else "assistant",
            avatar=":material/person:" if mensaje["autor"] == "cliente"
            else ":material/support_agent:",
        ):
            st.write(mensaje["texto"])
            st.caption("Vos" if mensaje["autor"] == "cliente" else
                       ("Soporte · respuesta corregida" if mensaje["tipo"] == "rectificacion"
                        else "Soporte"))
    if mensajes and mensajes[-1]["autor"] == "cliente":
        st.caption("Soporte todavía no respondió a este último mensaje.")
    nuevo_mensaje = st.chat_input("Escribí otro mensaje a soporte")
    if nuevo_mensaje:
        try:
            post(f"/reclamos/{elegido}/mensajes/cliente", {
                "cliente_id": cliente["id"], "texto": nuevo_mensaje.strip(),
            })
        except APIError as error:
            st.error(str(error))
        else:
            st.rerun()
