"""Interfaz para operar tickets y revisar análisis de SupportOps."""

import streamlit as st

from api_client import APIError, API_URL, get, post


st.set_page_config(page_title="SupportOps", page_icon=":material/support_agent:", layout="wide")


def mostrar_error(error: APIError):
    st.error(str(error), icon=":material/error:")


def resumen():
    st.header("Resumen")
    st.caption("Recorrido de la demostración: cliente crea una consulta, la IA propone y soporte decide qué respuesta mostrar.")
    try:
        kpis = get("/kpis")
        ultimos = get("/tickets", limit=10)
    except APIError as error:
        mostrar_error(error)
        return

    with st.container(horizontal=True):
        st.metric("Tickets", kpis["tickets"], border=True)
        st.metric("Abiertos", kpis["abiertos"], border=True)
        st.metric("Resueltos", kpis["resueltos"], border=True)

    with st.container(border=True):
        st.subheader("Primeros tickets")
        st.caption("La muestra es ficticia. La tabla muestra hasta diez tickets.")
        st.dataframe(
            [{clave: ticket[clave] for clave in ("id", "cliente", "plan", "estado", "texto")}
             for ticket in ultimos["tickets"]],
            hide_index=True,
        )


def tickets():
    st.header("Tickets")
    plan = st.selectbox("Plan", ["Todos", "Basic", "Pro", "Enterprise"])
    pagina = st.number_input("Página", min_value=1, value=1, step=1)
    parametros = {"limit": 20, "offset": (pagina - 1) * 20}
    if plan != "Todos":
        parametros["plan"] = plan
    try:
        listado = get("/tickets", **parametros)
    except APIError as error:
        mostrar_error(error)
        return

    st.caption(f"{listado['cantidad']} tickets encontrados · 20 por página")
    if listado["tickets"]:
        st.dataframe(
            [{clave: ticket[clave] for clave in ("id", "cliente", "plan", "prioridad", "estado", "texto")}
             for ticket in listado["tickets"]],
            hide_index=True,
        )
    else:
        st.info("No hay tickets en esta página.")

    st.subheader("Ver un ticket")
    ticket_id = st.number_input("ID del ticket", min_value=1, value=1, step=1,
                                key="ticket_detalle_id")
    if st.button("Abrir ticket", icon=":material/visibility:"):
        try:
            st.session_state.ticket_detalle = get(f"/tickets/{ticket_id}")
        except APIError as error:
            mostrar_error(error)
    detalle = st.session_state.get("ticket_detalle")
    if detalle and detalle["id"] == ticket_id:
        with st.container(border=True):
            st.write(f"**Ticket #{detalle['id']} · {detalle['cliente']} · {detalle['estado']}**")
            st.write(detalle["texto"])
            st.caption(f"Plan: {detalle['plan']} · Prioridad: {detalle['prioridad']}")
            if detalle["eventos"]:
                st.dataframe(detalle["eventos"], hide_index=True)

    st.subheader("Crear ticket")
    try:
        clientes = get("/clientes")["clientes"]
    except APIError as error:
        mostrar_error(error)
        return
    if not clientes:
        st.info("Todavía no hay clientes. Ejecutá bootstrap.py para cargar la muestra.")
        return
    with st.form("crear_ticket"):
        cliente = st.selectbox(
            "Cliente",
            clientes,
            format_func=lambda c: f"{c['nombre']} · {c['plan']} (ID {c['id']})",
        )
        texto = st.text_area("Consulta", placeholder="Describí el problema en al menos 10 caracteres")
        enviar = st.form_submit_button("Crear ticket", icon=":material/add:")
    if enviar:
        try:
            creado = post("/tickets", {"cliente_id": cliente["id"], "texto": texto})
            st.success(f"Ticket #{creado['id']} creado.")
            st.session_state.ticket_para_analizar = creado["id"]
            st.session_state.ticket_analizar_id = creado["id"]
        except APIError as error:
            mostrar_error(error)


def analisis():
    st.header("Análisis y revisión humana")
    st.caption("Cada análisis consulta a Ollama y guarda una ejecución en PostgreSQL.")
    st.session_state.setdefault(
        "ticket_analizar_id", st.session_state.get("ticket_para_analizar", 1)
    )
    ticket_id = st.number_input(
        "ID del ticket a analizar", min_value=1, step=1,
        key="ticket_analizar_id",
    )
    try:
        ticket = get(f"/tickets/{ticket_id}")
    except APIError as error:
        mostrar_error(error)
        return
    with st.container(border=True):
        st.write(f"**Ticket #{ticket_id} · {ticket['cliente']}**")
        st.write(ticket["texto"])

    if st.button("Analizar ticket", type="primary", icon=":material/psychology:"):
        with st.spinner("Analizando con Ollama; puede tardar un momento..."):
            try:
                nuevo = post(f"/tickets/{ticket_id}/analizar", timeout=180)
                st.session_state.ultima_ejecucion = nuevo["ejecucion_id"]
                st.success(f"Análisis guardado como ejecución #{nuevo['ejecucion_id']}.")
            except APIError as error:
                mostrar_error(error)

    try:
        ejecuciones = get(f"/tickets/{ticket_id}/ejecuciones")["ejecuciones"]
    except APIError as error:
        mostrar_error(error)
        return
    if not ejecuciones:
        st.info("Este ticket todavía no tiene análisis. Usá el botón para crear uno.")
        return

    ids = [ejecucion["id"] for ejecucion in ejecuciones]
    elegido = st.session_state.get("ultima_ejecucion")
    indice = ids.index(elegido) if elegido in ids else 0
    ejecucion_id = st.selectbox("Ejecución para revisar", ids, index=indice,
                                format_func=lambda n: f"Ejecución #{n}")
    try:
        ejecucion = get(f"/ejecuciones/{ejecucion_id}")
    except APIError as error:
        mostrar_error(error)
        return

    resultado = ejecucion["resultado"]
    triage = resultado.get("triage", {})
    borrador = resultado.get("borrador", {})
    supervision = resultado.get("supervision", {})
    with st.container(border=True):
        st.subheader("Resultado")
        st.write(f"**Categoría:** {triage.get('categoria', 'sin clasificar')}")
        st.write(f"**Decisión automática:** {supervision.get('decision', 'sin decisión')}")
        st.write(f"**Borrador:** {borrador.get('texto', '')}")
        st.write(f"**Citas:** {', '.join(borrador.get('citas', [])) or 'ninguna'}")
        st.write("**Evidencia consultada**")
        if resultado.get("evidencia"):
            for documento in resultado["evidencia"]:
                etiqueta = f"{documento.get('id', '?')} · {documento.get('titulo', '')}"
                with st.expander(etiqueta):
                    st.caption(f"Versión {documento.get('version', 'sin indicar')}")
                    st.write(documento.get("texto", "Sin contenido"))
        else:
            st.caption("No hay documentos recuperados. La respuesta necesita revisión humana.")
        with st.expander("Ver recorrido de agentes y análisis completo"):
            st.json(resultado)

    if ejecucion.get("alerta_seguridad"):
        st.warning(ejecucion["alerta_seguridad"])
    if ejecucion["revision"]:
        st.subheader("Decisión y correcciones")
        try:
            historial = get(f"/ejecuciones/{ejecucion_id}/historial")
        except APIError as error:
            mostrar_error(error)
            return
        vigente = historial["vigente"]
        st.write(f"**Decisión vigente:** {vigente['decision']}")
        if vigente.get("texto_final"):
            st.write(vigente["texto_final"])
        st.caption(f"Motivo: {vigente['motivo']}")
        registros = [
            {"versión": 1, "decisión": historial["original"]["decision"],
             "motivo": historial["original"]["motivo"],
             "fecha": historial["original"]["creado"]}
        ]
        registros.extend(
            {"versión": numero, "decisión": c["decision"],
             "motivo": c["motivo"], "fecha": c["creado"]}
            for numero, c in enumerate(historial["correcciones"], start=2)
        )
        with st.expander("Ver historial completo"):
            st.dataframe(registros, hide_index=True)
        with st.expander("Corregir una decisión anterior"):
            st.caption("La versión anterior se conserva. Si el cliente ya la vio, verá una rectificación.")
            with st.form(f"corregir_{ejecucion_id}"):
                decision_nueva = st.segmented_control(
                    "Nueva decisión", ["editar", "rechazar"], default="editar"
                )
                respuesta_nueva = st.text_area("Respuesta corregida")
                motivo_nuevo = st.text_area("Motivo de la corrección")
                operador = st.text_input("Operador", value="Operador demo")
                corregir = st.form_submit_button("Guardar corrección")
            if corregir:
                try:
                    post(f"/ejecuciones/{ejecucion_id}/correcciones", {
                        "decision": decision_nueva,
                        "texto_final": respuesta_nueva,
                        "motivo": motivo_nuevo,
                        "operador": operador,
                    })
                except APIError as error:
                    mostrar_error(error)
                else:
                    st.success("Corrección guardada sin borrar la versión anterior.")
                    st.rerun()
        return

    st.subheader("Registrar revisión")
    bloqueado = supervision.get("decision") == "bloquear" or bool(ejecucion.get("alerta_seguridad"))
    opciones = ["rechazar"] if bloqueado else ["aprobar", "editar", "rechazar"]
    with st.form(f"revision_{ejecucion_id}"):
        decision = st.segmented_control("Decisión", opciones, default=opciones[0])
        texto_final = st.text_area("Texto final (solo si editás)")
        motivo = st.text_area("Motivo de la revisión")
        guardar = st.form_submit_button("Guardar revisión", icon=":material/save:")
    if guardar:
        try:
            revision = post(
                f"/ejecuciones/{ejecucion_id}/revision",
                {"decision": decision, "texto_final": texto_final, "motivo": motivo},
            )
            st.success(f"Revisión #{revision['id']} guardada: {revision['decision']}.")
            st.caption("Se guardó la decisión. No se envió ningún mensaje al cliente.")
            st.rerun()
        except APIError as error:
            mostrar_error(error)


def simulacion():
    st.header("Simulación de atención")
    st.caption(
        "Escribí como cliente. La IA prepara una propuesta y vos, como operador, "
        "decidís qué responder. Cada consulta crea un ticket ficticio."
    )
    st.info(
        "La conversación de esta pantalla dura mientras la pestaña esté abierta. "
        "Los tickets, análisis y revisiones sí quedan guardados en PostgreSQL. "
        "Cada consulta se analiza por separado, sin recordar las anteriores."
    )

    try:
        clientes = get("/clientes")["clientes"]
    except APIError as error:
        mostrar_error(error)
        return
    if not clientes:
        st.warning("Primero cargá los clientes ficticios con 01_PREPARAR_NETBOOK.cmd.")
        return

    turnos = st.session_state.setdefault("sim_turnos", [])
    if st.button("Nueva conversación", disabled=not turnos):
        st.session_state.sim_turnos = []
        st.rerun()

    cliente = st.selectbox(
        "Cliente ficticio",
        clientes,
        format_func=lambda c: f"{c['nombre']} · {c['plan']}",
        disabled=bool(turnos),
        key="sim_cliente",
    )

    for turno in turnos:
        with st.chat_message("user"):
            st.write(turno["pregunta"])
            st.caption(f"Ticket #{turno['ticket_id']}")
        revision = turno.get("revision")
        if revision:
            with st.chat_message("assistant"):
                if revision["decision"] == "rechazar":
                    st.write("El operador rechazó la propuesta. No se preparó una respuesta para el cliente.")
                else:
                    st.write(revision["texto_final"])
                    st.caption(f"Respuesta revisada por el operador · ejecución #{turno['ejecucion_id']}")

    pendiente = turnos[-1] if turnos and not turnos[-1].get("revision") else None
    if pendiente:
        if "ejecucion_id" not in pendiente:
            if st.button("Pedir propuesta a la IA", type="primary"):
                with st.spinner("Ollama está analizando esta consulta..."):
                    try:
                        resultado = post(
                            f"/tickets/{pendiente['ticket_id']}/analizar", timeout=180
                        )
                    except APIError as error:
                        mostrar_error(error)
                    else:
                        pendiente["ejecucion_id"] = resultado["ejecucion_id"]
                        st.rerun()
        else:
            try:
                ejecucion = get(f"/ejecuciones/{pendiente['ejecucion_id']}")
            except APIError as error:
                mostrar_error(error)
                return
            if ejecucion["revision"]:
                pendiente["revision"] = ejecucion["revision"]
                st.rerun()

            resultado = ejecucion["resultado"]
            supervision = resultado.get("supervision", {})
            borrador = resultado.get("borrador", {})
            with st.container(border=True):
                st.subheader("Propuesta para el operador")
                st.write(f"**Categoría:** {resultado.get('triage', {}).get('categoria', 'sin clasificar')}")
                st.write(f"**Decisión automática:** {supervision.get('decision', 'sin decisión')}")
                st.write(f"**Borrador:** {borrador.get('texto', '')}")
                st.write(f"**Citas:** {', '.join(borrador.get('citas', [])) or 'ninguna'}")
                for documento in resultado.get("evidencia", []):
                    with st.expander(f"{documento.get('id', '?')} · {documento.get('titulo', '')}"):
                        st.write(documento.get("texto", "Sin contenido"))
                if not resultado.get("evidencia"):
                    st.warning("No se encontró información de respaldo. Revisá el borrador con cuidado.")

            bloqueado = supervision.get("decision") == "bloquear" or bool(
                ejecucion.get("alerta_seguridad")
            )
            opciones = ["rechazar"] if bloqueado else ["aprobar", "editar", "rechazar"]
            if bloqueado:
                st.warning("Esta propuesta está bloqueada; solo se puede rechazar.")
            with st.form(f"sim_revision_{pendiente['ejecucion_id']}"):
                decision = st.radio("Decisión del operador", opciones, horizontal=True)
                texto_final = st.text_area("Respuesta corregida (si elegís editar)")
                motivo = st.text_area("Motivo de la decisión")
                guardar = st.form_submit_button("Guardar decisión")
            if guardar:
                try:
                    revision = post(
                        f"/ejecuciones/{pendiente['ejecucion_id']}/revision",
                        {"decision": decision, "texto_final": texto_final, "motivo": motivo},
                    )
                except APIError as error:
                    mostrar_error(error)
                else:
                    pendiente["revision"] = revision
                    st.rerun()
    else:
        pregunta = st.chat_input("Escribí una consulta como cliente ficticio")
        if pregunta:
            if not 10 <= len(pregunta.strip()) <= 4000:
                st.error("La consulta debe tener entre 10 y 4000 caracteres.")
            else:
                try:
                    ticket = post(
                        "/tickets", {"cliente_id": cliente["id"], "texto": pregunta.strip()}
                    )
                except APIError as error:
                    mostrar_error(error)
                else:
                    turnos.append({"ticket_id": ticket["id"], "pregunta": pregunta.strip()})
                    st.rerun()


def productos_soporte():
    st.header("Productos y pedidos")
    st.caption("Catálogo y compras ficticias de la tienda local.")
    try:
        productos = get("/productos")["productos"]
        pedidos = get("/pedidos")["pedidos"]
    except APIError as error:
        mostrar_error(error)
        return
    st.subheader("Catálogo")
    st.dataframe(
        [{"Código": p["id"], "Producto": p["nombre"],
          "Categoría": p["categoria"], "Precio": p["precio"],
          "Unidades": p["stock"]} for p in productos],
        hide_index=True,
    )
    st.subheader("Pedidos simulados recientes")
    if pedidos:
        st.dataframe(
            [{"Pedido": p["id"], "Cliente": p["cliente"],
              "Producto": p["producto"], "Cantidad": p["cantidad"],
              "Total": p["total"]} for p in pedidos],
            hide_index=True,
        )
    else:
        st.caption("Todavía no hay pedidos.")


def reclamos_soporte():
    st.header("Bandeja de reclamos")
    st.caption("Abrí un caso pendiente para analizarlo. Después revisá la propuesta y guardá tu decisión.")
    st.button("Actualizar bandeja", icon=":material/refresh:")
    try:
        reclamos = get("/reclamos")["reclamos"]
    except APIError as error:
        mostrar_error(error)
        return
    if not reclamos:
        st.info("No hay reclamos nuevos.")
        return
    filtro = st.segmented_control("Mostrar", ["Pendientes", "Todos"], default="Pendientes")
    if filtro == "Pendientes":
        reclamos = [r for r in reclamos if r["estado"] == "abierto"]
    if not reclamos:
        st.info("No hay reclamos pendientes.")
        return
    for reclamo in reclamos:
        with st.container(border=True):
            st.write(
                f"**Ticket #{reclamo['ticket_id']} · {reclamo['cliente']}**"
            )
            st.caption(
                f"Reclamo #{reclamo['id']} · {reclamo['estado']} · "
                f"{reclamo.get('producto') or 'Consulta general'}"
                + (f" · Pedido #{reclamo['pedido_id']}" if reclamo.get("pedido_id") else "")
            )
            st.write(reclamo["texto"])
            if st.button("Abrir ticket", key=f"abrir_{reclamo['ticket_id']}"):
                st.session_state.ticket_analizar_id = reclamo["ticket_id"]
                st.session_state.ir_analisis = True
                st.rerun()


st.title("SupportOps")
st.caption("Panel de soporte · Tienda Faro ficticia · Ollama local")
if st.session_state.pop("ir_analisis", False):
    st.session_state.seccion = "Análisis y revisión"
with st.sidebar:
    seccion = st.radio(
        "Sección",
        ["Resumen", "Reclamos", "Productos y pedidos", "Tickets",
         "Análisis y revisión", "Simulación"],
        key="seccion",
    )
    st.caption(f"API: {API_URL}")

try:
    get("/health")
except APIError as error:
    st.error("La API no está disponible. Iniciá `run.py` en otra terminal.")
    mostrar_error(error)
    st.stop()

if seccion == "Resumen":
    resumen()
elif seccion == "Tickets":
    tickets()
elif seccion == "Reclamos":
    reclamos_soporte()
elif seccion == "Productos y pedidos":
    productos_soporte()
elif seccion == "Análisis y revisión":
    analisis()
else:
    simulacion()
