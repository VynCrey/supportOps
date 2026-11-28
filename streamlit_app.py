"""Interfaz para operar tickets y revisar análisis de SupportOps."""

import streamlit as st

from api_client import APIError, API_URL, get, post


st.set_page_config(page_title="SupportOps | Soporte", page_icon=":material/support_agent:", layout="wide")
st.html("""<style>
.stApp {background: #f7f9f9;}
.block-container {max-width: 1180px; padding-top: 2rem;}
[data-testid="stChatMessage"] {border: 1px solid #dce7e5; border-radius: 16px;
    background: white; margin-bottom: .45rem;}
h1, h2, h3 {color: #173d44;}
</style>""")


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
    st.header("Revisar una propuesta de IA")
    st.caption("La IA prepara una respuesta al último mensaje. Solo tu aprobación o edición la muestra al cliente.")
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

    try:
        conversacion = get(f"/reclamos/{ticket_id}/mensajes")["mensajes"]
    except APIError:
        conversacion = None  # Los tickets de práctica no tienen conversación.
    if conversacion:
        with st.expander("Ver conversación con el cliente", expanded=True):
            for mensaje in conversacion:
                with st.chat_message(
                    "user" if mensaje["autor"] == "cliente" else "assistant",
                    avatar=":material/person:" if mensaje["autor"] == "cliente"
                    else ":material/support_agent:",
                ):
                    st.write(mensaje["texto"])
        st.caption("El análisis tomará el último mensaje del cliente y el contexto reciente.")

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
            st.caption(
                "Si es una conversación, aprobar o editar muestra la respuesta en el chat del cliente. "
                "Rechazar no envía el borrador."
            )
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
    st.header("Bandeja de conversaciones")
    st.caption("El asistente responde consultas sencillas. Revisá las demás propuestas aquí antes de publicarlas.")
    st.button("Actualizar conversaciones", icon=":material/refresh:")
    try:
        reclamos = get("/reclamos")["reclamos"]
    except APIError as error:
        mostrar_error(error)
        return
    if not reclamos:
        st.info("No hay reclamos nuevos.")
        return
    filtro = st.segmented_control("Mostrar", ["Todas", "Abiertas"], default="Todas")
    visibles = ([r for r in reclamos if r["estado"] == "abierto"]
               if filtro == "Abiertas" else reclamos)
    if not visibles:
        st.info("No hay conversaciones en esta vista. Probá con «Todas».")
        return
    por_id = {r["ticket_id"]: r for r in visibles}
    elegido = st.selectbox(
        "Elegí una conversación", list(por_id),
        format_func=lambda n: f"#{n} · {por_id[n]['cliente']} · {por_id[n]['texto'][:65]}",
        key="soporte_conversacion",
    )
    reclamo = por_id[elegido]
    st.caption(
        f"{reclamo['estado'].capitalize()} · {reclamo.get('producto') or 'Consulta general'}"
        + (f" · Pedido #{reclamo['pedido_id']}" if reclamo.get("pedido_id") else "")
    )
    try:
        mensajes = get(f"/reclamos/{elegido}/mensajes")["mensajes"]
        fotos = get(f"/reclamos/{elegido}/fotos")["fotos"]
    except APIError as error:
        mostrar_error(error)
        return
    for mensaje in mensajes:
        with st.chat_message(
            "user" if mensaje["autor"] == "cliente" else "assistant",
            avatar=":material/person:" if mensaje["autor"] == "cliente"
            else ":material/support_agent:",
        ):
            st.write(mensaje["texto"])
            st.caption(reclamo["cliente"] if mensaje["autor"] == "cliente" else
                       ("Asistente · automática" if mensaje["tipo"] == "automatica" else
                        "Soporte · rectificada" if mensaje["tipo"] == "rectificacion"
                        else "Soporte"))
            if mensaje["autor"] == "soporte" and mensaje["tipo"] in (
                "mensaje", "rectificacion", "automatica"
            ):
                with st.expander("Corregir este mensaje"):
                    with st.form(f"rectificar_mensaje_{mensaje['id']}"):
                        texto_nuevo = st.text_area("Respuesta corregida", value=mensaje["texto"])
                        motivo = st.text_input("Por qué lo corregís")
                        corregir = st.form_submit_button("Publicar corrección")
                    if corregir:
                        try:
                            post(f"/reclamos/{elegido}/mensajes/{mensaje['id']}/rectificar", {
                                "texto": texto_nuevo, "motivo": motivo,
                            })
                        except APIError as error:
                            mostrar_error(error)
                        else:
                            st.rerun()
    for foto in fotos:
        st.image(f"{API_URL}/reclamos/{elegido}/fotos/{foto['id']}",
                 caption="Foto enviada por el cliente ficticio", width=240)

    try:
        propuesta = get(f"/reclamos/{elegido}/propuesta")
    except APIError as error:
        mostrar_error(error)
        propuesta = {}
    if propuesta.get("estado") == "preparando":
        st.info("La propuesta para el último mensaje se está preparando. Actualizá en unos segundos.")
    elif propuesta.get("estado") == "error":
        st.warning(propuesta.get("detalle") or "No se pudo preparar la propuesta.")
    elif propuesta.get("estado") == "listo" and propuesta.get("ejecucion_id"):
        ejecucion = get(f"/ejecuciones/{propuesta['ejecucion_id']}")
        resultado = ejecucion["resultado"]
        with st.container(border=True):
            st.subheader("Propuesta para revisar")
            st.write(resultado.get("borrador", {}).get("texto", ""))
            st.caption("Documentos: " +
                       (", ".join(resultado.get("borrador", {}).get("citas", [])) or "ninguno"))
            st.caption("Control: " + resultado.get("supervision", {}).get("decision", "revisar"))
            if not ejecucion.get("revision"):
                bloqueado = resultado.get("supervision", {}).get("decision") == "bloquear"
                opciones = ["rechazar"] if bloqueado else ["aprobar", "editar", "rechazar"]
                with st.form(f"revision_chat_{propuesta['ejecucion_id']}"):
                    decision = st.segmented_control("Tu decisión", opciones,
                                                    default=opciones[0])
                    texto_final = st.text_area("Respuesta corregida (si editás)")
                    motivo = st.text_input("Motivo de la decisión")
                    guardar = st.form_submit_button("Guardar y publicar decisión", type="primary")
                if guardar:
                    try:
                        post(f"/ejecuciones/{propuesta['ejecucion_id']}/revision", {
                            "decision": decision, "texto_final": texto_final,
                            "motivo": motivo,
                        })
                    except APIError as error:
                        mostrar_error(error)
                    else:
                        st.rerun()
            else:
                st.success("Esta propuesta ya fue revisada.")
    with st.expander("Historial de cambios del chat"):
        try:
            historial = get(f"/reclamos/{elegido}/mensajes/historial")["mensajes"]
        except APIError as error:
            mostrar_error(error)
        else:
            st.dataframe(
                [{"fecha": m["creado"], "autor": m["autor"],
                  "mensaje": m["texto"], "vigente": m["vigente"],
                  "motivo de corrección": m.get("motivo") or ""}
                 for m in historial],
                hide_index=True,
            )
    if st.button("Volver a preparar propuesta"):
        with st.spinner("Ollama está preparando una propuesta para que la revises..."):
            try:
                nuevo = post(f"/tickets/{elegido}/analizar", timeout=180)
            except APIError as error:
                mostrar_error(error)
            else:
                st.session_state.ultima_ejecucion = nuevo["ejecucion_id"]
                st.session_state.ticket_analizar_id = elegido
                st.session_state.ir_analisis = True
                st.rerun()
    st.caption("La propuesta de IA no se muestra al cliente hasta que la revises.")
    st.caption("También podés escribir una respuesta propia y enviarla con Enter.")
    respuesta = st.chat_input("Escribí una respuesta como soporte")
    if respuesta:
        try:
            post(f"/reclamos/{elegido}/mensajes/soporte", {"texto": respuesta.strip()})
        except APIError as error:
            mostrar_error(error)
        else:
            st.rerun()


st.title("SupportOps · Soporte")
st.caption("Tienda Faro ficticia · bandeja de atención con asistente local")
if st.session_state.pop("ir_analisis", False):
    st.session_state.seccion = "Análisis y revisión"
opciones_seccion = ["Bandeja", "Productos y pedidos", "Resumen", "Análisis y revisión", "Tickets"]
if st.session_state.get("seccion") not in opciones_seccion:
    st.session_state.seccion = "Bandeja"
with st.sidebar:
    seccion = st.radio(
        "Sección",
        opciones_seccion,
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
elif seccion == "Bandeja":
    reclamos_soporte()
elif seccion == "Productos y pedidos":
    productos_soporte()
elif seccion == "Análisis y revisión":
    analisis()
else:
    reclamos_soporte()
