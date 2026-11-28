"""Interfaz para operar tickets y revisar análisis de SupportOps."""

import streamlit as st

from api_client import APIError, get, post
from chat_ui import aplicar_estilos, chat_en_vivo, marca, vista_previa


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


@st.fragment(run_every="4s")
def bandeja_en_vivo():
    st.subheader("Conversaciones")
    try:
        chats = get("/reclamos")["reclamos"]
    except APIError as error:
        mostrar_error(error)
        return
    pendientes = sum(bool(c.get("necesita_soporte")) for c in chats)
    st.caption(f"Por responder: {pendientes}")
    filtro = st.segmented_control("Filtrar conversaciones", ["Todas", "Por responder"],
                                  default="Todas", label_visibility="collapsed")
    if filtro == "Por responder":
        chats = [c for c in chats if c.get("necesita_soporte")]
    if not chats:
        st.caption("No hay conversaciones en esta vista.")
        return
    with st.container(height=390, key="faro_bandeja_lista"):
        for chat in chats:
            ticket_id = chat["ticket_id"]
            elegido = ticket_id == st.session_state.faro_conversacion_soporte
            extracto = vista_previa(chat.get("ultimo_texto") or chat["texto"], 42)
            nombre = chat["cliente"]
            icono = ":material/mark_chat_unread:" if chat.get("necesita_soporte") else ":material/chat:"
            if st.button(f"{nombre} · #{ticket_id}\n\n{extracto}", width="stretch",
                         icon=icono, key=f"faro_bandeja_{ticket_id}",
                         type="primary" if elegido else "secondary"):
                st.session_state.faro_conversacion_soporte = ticket_id
                st.rerun()


@st.fragment(run_every="3s")
def propuesta_en_vivo(ticket_id):
    try:
        propuesta = get(f"/reclamos/{ticket_id}/propuesta")
        estado = propuesta["estado"]
        if estado == "respondido":
            return
        ejecucion_id = propuesta.get("ejecucion_id")
        ejecucion = get(f"/ejecuciones/{ejecucion_id}") if estado == "listo" and ejecucion_id else None
    except APIError:
        st.caption("Se está restableciendo la conexión con el asistente.")
        return

    with st.container(border=True, key="faro_propuesta"):
        st.subheader("Propuesta privada")
        if estado == "preparando":
            st.caption("Preparando una respuesta. Podés contestar por el chat mientras tanto.")
            return
        if ejecucion is None:
            if estado == "error":
                st.warning(propuesta.get("detalle") or "La preparación se interrumpió.")
            elif estado == "rechazado":
                st.caption("Propuesta rechazada. El cliente todavía espera una respuesta.")
            else:
                st.caption("Podés pedir una sugerencia para el último mensaje.")
            if st.button("Reintentar" if estado == "error" else "Preparar propuesta",
                         icon=":material/auto_awesome:", key=f"faro_reintentar_{ticket_id}"):
                try:
                    post(f"/reclamos/{ticket_id}/propuesta")
                except APIError as error:
                    mostrar_error(error)
                else:
                    st.rerun()
            return

        resultado = ejecucion["resultado"]
        sugerencia = resultado.get("borrador", {}).get("texto", "")
        st.text(sugerencia)
        diagnostico = resultado.get("supervision", {})
        with st.expander("Fuentes y motivos de la revisión"):
            for documento in resultado.get("evidencia", []):
                st.text(f"{documento['id']} · {documento.get('titulo') or documento['id']}")
                st.text(documento["texto"])
            if not resultado.get("evidencia"):
                st.caption("No se consultaron documentos para esta propuesta.")
            for motivo in diagnostico.get("motivos", []):
                st.text(motivo)
        bloqueado = (diagnostico.get("decision") == "bloquear"
                     or bool(ejecucion.get("advertencia_seguridad")))
        if bloqueado:
            st.warning("La propuesta está bloqueada. Podés rechazarla y escribir una respuesta propia.")
        nombres = {"aprobar": "Enviar propuesta", "editar": "Editar y enviar", "rechazar": "Rechazar"}
        opciones = ["rechazar"] if bloqueado else list(nombres)
        decision = st.segmented_control("Decisión", opciones, format_func=nombres.__getitem__,
                                         default="rechazar" if bloqueado else None,
                                         key=f"faro_decision_{ejecucion_id}")
        if decision is None:
            return
        clave_error = f"faro_revision_error_{ejecucion_id}"
        if st.session_state.get(clave_error):
            st.error(st.session_state[clave_error])
        with st.form(f"faro_revision_{ejecucion_id}_{decision}", enter_to_submit=False, border=False):
            texto_final = (st.text_area("Respuesta para el cliente", value=sugerencia, max_chars=8000)
                           if decision == "editar" else "")
            motivo = st.text_input("Motivo de la decisión", max_chars=1000)
            guardar = st.form_submit_button(
                "Registrar rechazo" if decision == "rechazar" else "Enviar al cliente",
                type="primary",
            )
        if guardar:
            try:
                post(f"/ejecuciones/{ejecucion_id}/revision", {
                    "decision": decision, "texto_final": texto_final, "motivo": motivo,
                })
            except APIError as error:
                st.session_state[clave_error] = str(error)
                st.rerun()
            else:
                st.session_state.pop(clave_error, None)
                st.rerun()


def responder(ticket_id):
    clave = f"faro_soporte_escribe_{ticket_id}"
    fallido = st.session_state.pop(f"{clave}_error", None)
    if fallido:
        st.error(fallido["error"], icon=":material/error:")
        st.session_state[clave] = fallido["texto"]
    with st.container(key="faro_soporte_compositor"):
        texto = st.chat_input("Escribí una respuesta al cliente", key=clave, max_chars=8000)
    if texto:
        try:
            post(f"/reclamos/{ticket_id}/mensajes/soporte", {"texto": texto.strip()})
        except APIError as error:
            st.session_state[f"{clave}_error"] = {"error": str(error), "texto": texto}
        st.rerun()


def corregir_respuesta(ticket_id):
    with st.expander("Corregir una respuesta o ver el historial", on_change="rerun",
                     key=f"faro_correcciones_{ticket_id}") as panel:
        if not panel.open:
            return
        try:
            historial = get(f"/reclamos/{ticket_id}/mensajes/historial")["mensajes"]
        except APIError as error:
            mostrar_error(error)
            return
        respuestas = {m["id"]: m for m in historial if m["autor"] == "soporte" and m["vigente"]}
        if respuestas:
            mensaje_id = st.selectbox("Respuesta", list(reversed(respuestas)),
                                      format_func=lambda n: vista_previa(respuestas[n]["texto"]))
            mensaje = respuestas[mensaje_id]
            with st.form(f"faro_corregir_{mensaje_id}"):
                texto = st.text_area("Respuesta corregida", value=mensaje["texto"], max_chars=8000)
                motivo = st.text_input("Motivo de la corrección", max_chars=1000)
                guardar = st.form_submit_button("Publicar corrección")
            if guardar:
                try:
                    if mensaje.get("ejecucion_id"):
                        post(f"/ejecuciones/{mensaje['ejecucion_id']}/correcciones", {
                            "decision": "editar", "texto_final": texto, "motivo": motivo,
                        })
                    else:
                        post(f"/reclamos/{ticket_id}/mensajes/{mensaje_id}/rectificar", {
                            "texto": texto, "motivo": motivo,
                        })
                except APIError as error:
                    mostrar_error(error)
                else:
                    st.rerun()
        versiones = [{
            "Mensaje": vista_previa(m["texto"], 100),
            "Autor": m["autor"].capitalize(),
            "Estado": "Vigente" if m["vigente"] else "Anterior",
            "Motivo de corrección": m.get("motivo") or "",
        } for m in historial]
        if versiones:
            st.dataframe(versiones, hide_index=True)


def reclamos_soporte():
    if "faro_conversacion_soporte" not in st.session_state:
        try:
            chats = get("/reclamos")["reclamos"]
        except APIError as error:
            mostrar_error(error)
            return
        primero = next((c for c in chats if c.get("necesita_soporte")), chats[0] if chats else None)
        st.session_state.faro_conversacion_soporte = primero["ticket_id"] if primero else None
    elegido = st.session_state.faro_conversacion_soporte
    lista, detalle = st.columns([1, 2.25], gap="medium")
    with lista:
        bandeja_en_vivo()
    with detalle:
        if elegido is None:
            st.info("Elegí una conversación de la bandeja.")
            return
        chat_en_vivo(elegido, get)
        responder(elegido)
        propuesta_en_vivo(elegido)
        corregir_respuesta(elegido)


st.set_page_config(page_title="SupportOps | Soporte", page_icon=":material/support_agent:",
                   layout="wide", initial_sidebar_state="collapsed")
aplicar_estilos()
marca("SupportOps", "Mesa de ayuda de Tienda Faro")
vista = st.segmented_control("Secciones de soporte", ["Bandeja", "Productos y pedidos", "Evaluación"],
                             default="Bandeja", label_visibility="collapsed", key="faro_vista_soporte")

try:
    get("/health")
except APIError as error:
    st.error("Iniciá 02_INICIAR_API.cmd para conectar la mesa de ayuda.")
    mostrar_error(error)
    st.stop()

if vista == "Productos y pedidos":
    productos_soporte()
elif vista == "Evaluación":
    seccion = st.segmented_control("Pruebas del proyecto", ["Resumen", "Tickets", "Análisis y revisión"],
                                    default="Resumen", label_visibility="collapsed")
    if seccion == "Tickets":
        tickets()
    elif seccion == "Análisis y revisión":
        analisis()
    else:
        resumen()
else:
    reclamos_soporte()
