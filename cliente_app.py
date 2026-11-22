"""Vista del cliente ficticio; nunca muestra prompts ni propuestas sin revisión."""

import streamlit as st

from api_client import APIError, get, post
from pdf_guard import extraer_pdf


st.set_page_config(
    page_title="Tienda Faro | Cliente", page_icon=":material/storefront:",
    layout="wide",
)


def dinero(valor):
    return f"${float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


st.title("Tienda Faro")
st.caption("Tienda ficticia · compras de demostración · soporte revisado por una persona")

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
    seccion = st.radio("Sección", ["Catálogo", "Mis pedidos", "Mis reclamos"])
    st.caption("Esta pantalla simula al cliente. No se realizan pagos reales.")


if seccion == "Catálogo":
    st.header("Productos")
    st.caption("Precios y disponibilidad ficticios. La compra se registra solo en esta computadora.")
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
    for producto in visibles:
        with st.container(border=True):
            izquierda, derecha = st.columns([3, 1], vertical_alignment="center")
            with izquierda:
                st.subheader(producto["nombre"])
                st.caption(f"{producto['categoria']} · Código {producto['id']}")
                st.write(producto["descripcion"])
            with derecha:
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
                        st.success(f"Pedido simulado #{pedido['id']} registrado.")

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
    st.header("Mis reclamos y consultas")
    st.caption("Describí el problema. El equipo de soporte revisará la propuesta de la IA antes de responder.")
    try:
        pedidos = get("/pedidos", cliente_id=cliente["id"])["pedidos"]
        reclamos = get("/reclamos", cliente_id=cliente["id"])["reclamos"]
        productos = get("/productos")["productos"]
    except APIError as error:
        st.error(str(error))
        st.stop()

    with st.form("nuevo_reclamo"):
        pedido = st.selectbox(
            "Pedido relacionado (opcional)", [None, *pedidos],
            format_func=lambda p: "Sin pedido" if p is None else f"#{p['id']} · {p['producto']}",
        )
        producto = st.selectbox(
            "Producto relacionado (si no elegiste un pedido)", [None, *productos],
            format_func=lambda p: "Sin producto" if p is None else p["nombre"],
            help="Si elegiste un pedido, se usará el producto de ese pedido.",
        )
        texto = st.text_area(
            "Consulta o reclamo", placeholder="Por ejemplo: el auricular dejó de encender...",
            max_chars=4000,
        )
        archivo = st.file_uploader(
            "PDF de respaldo (opcional, máximo 2 MB y 5 páginas)", type=["pdf"],
            help="Se extrae solo el texto. El PDF no se guarda ni se ejecuta; "
                 "su contenido se trata como información no confiable.",
        )
        enviar = st.form_submit_button("Enviar reclamo", type="primary")
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
                st.success(f"Reclamo #{nuevo['reclamo_id']} registrado. Ticket #{nuevo['ticket_id']}.")
                st.rerun()

    if not reclamos:
        st.info("Todavía no hay reclamos para este cliente ficticio.")
    for reclamo in reclamos:
        with st.container(border=True):
            st.write(f"**Reclamo #{reclamo['id']} · ticket #{reclamo['ticket_id']}**")
            st.caption(f"Estado del ticket: {reclamo['estado']}")
            if reclamo.get("producto"):
                st.caption(f"Producto: {reclamo['producto']}")
            st.write(reclamo["texto"])
            try:
                respuesta = get(
                    f"/reclamos/{reclamo['ticket_id']}/respuesta",
                    cliente_id=cliente["id"],
                )
            except APIError as error:
                st.error(str(error))
                continue
            if respuesta["estado"] == "respondido":
                st.success("Respuesta revisada por soporte")
                st.write(respuesta["texto"])
                if respuesta.get("corregida"):
                    st.caption(f"Respuesta rectificada · versión {respuesta['version']}")
            elif respuesta["estado"] == "sin_respuesta":
                st.caption("Soporte está preparando una respuesta nueva.")
            else:
                st.caption("Pendiente de revisión por soporte.")
