"""Interfaz para operar tickets y revisar análisis de SupportOps."""

import streamlit as st

from api_client import APIError, API_URL, get, post


st.set_page_config(page_title="SupportOps", page_icon=":material/support_agent:", layout="wide")


def mostrar_error(error: APIError):
    st.error(str(error), icon=":material/error:")


def resumen():
    st.header("Resumen")
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
        except APIError as error:
            mostrar_error(error)


def analisis():
    st.header("Análisis y revisión humana")
    st.caption("Cada análisis consulta a Ollama y guarda una ejecución en PostgreSQL.")
    ticket_id = st.number_input(
        "ID del ticket a analizar", min_value=1,
        value=st.session_state.get("ticket_para_analizar", 1), step=1,
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
        st.subheader("Revisión guardada")
        st.json(ejecucion["revision"])
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


st.title("SupportOps")
st.caption("Panel local para soporte asistido por IA")
with st.sidebar:
    seccion = st.radio("Sección", ["Resumen", "Tickets", "Análisis y revisión", "Simulación"])
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
elif seccion == "Análisis y revisión":
    analisis()
else:
    simulacion()
