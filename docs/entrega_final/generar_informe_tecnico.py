"""Genera el informe técnico final y su índice a partir del estado del proyecto."""

from html import escape
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon


HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("SUPPORTOPS_REPORT_OUTPUT",
                          str(HERE / "SupportOps_Informe_Tecnico_2026.pdf")))
COVER = HERE / "portada_ia.png"
TEAL = colors.HexColor("#006F73")
TEAL_DARK = colors.HexColor("#07575A")
INK = colors.HexColor("#26343B")
GRAY = colors.HexColor("#596A72")
PALE = colors.HexColor("#EAF4F3")
ROW = colors.HexColor("#F5F8F8")
LINE = colors.HexColor("#C5D8D8")
PAGE_W, PAGE_H = A4

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

ST = {
    "title": ParagraphStyle("title", fontName="Arial-Bold", fontSize=27,
                            leading=32, textColor=TEAL_DARK, spaceAfter=10),
    "subtitle": ParagraphStyle("subtitle", fontName="Arial", fontSize=13,
                               leading=18, textColor=GRAY, spaceAfter=16),
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=16,
                         leading=20, textColor=TEAL_DARK, spaceBefore=8,
                         spaceAfter=11, keepWithNext=True),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=11.5,
                         leading=15, textColor=TEAL, spaceBefore=12,
                         spaceAfter=6, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="Arial", fontSize=9.2,
                           leading=13.4, textColor=INK, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Arial", fontSize=8,
                            leading=11.2, textColor=GRAY, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="Arial", fontSize=9.2,
                             leading=13.7, leftIndent=14, firstLineIndent=-8,
                             textColor=INK, spaceAfter=5),
    "th": ParagraphStyle("th", fontName="Arial-Bold", fontSize=8.2,
                         leading=11, textColor=colors.white),
    "td": ParagraphStyle("td", fontName="Arial", fontSize=8.1,
                         leading=11.3, textColor=INK),
    "toc1": ParagraphStyle("toc1", fontName="Arial", fontSize=10.3,
                           leading=17, textColor=INK, leftIndent=0,
                           firstLineIndent=0, spaceBefore=6),
    "caption": ParagraphStyle("caption", fontName="Arial", fontSize=8,
                              leading=11, alignment=TA_CENTER,
                              textColor=GRAY, spaceBefore=5),
}


class Report(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4, leftMargin=19 * mm,
                         rightMargin=19 * mm, topMargin=22 * mm,
                         bottomMargin=20 * mm, title="SupportOps | Informe técnico 2026",
                         author="Marco Medina y Cristian Monzón")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width,
                      self.height, leftPadding=0, bottomPadding=0,
                      rightPadding=0, topPadding=0)
        self.addPageTemplates(PageTemplate(id="normal", frames=[frame],
                                           onPage=self.page_chrome))

    def page_chrome(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(TEAL)
        canvas.rect(0, PAGE_H - 6 * mm, PAGE_W, 6 * mm, fill=1, stroke=0)
        canvas.setFont("Arial", 7.5)
        canvas.setFillColor(GRAY)
        canvas.drawString(19 * mm, PAGE_H - 13 * mm, "SUPPORTOPS  /  INFORME TÉCNICO")
        canvas.drawRightString(PAGE_W - 19 * mm, PAGE_H - 13 * mm, "2026")
        canvas.setStrokeColor(LINE)
        canvas.line(19 * mm, 16 * mm, PAGE_W - 19 * mm, 16 * mm)
        canvas.drawString(19 * mm, 11 * mm, "Marco Medina  ·  Cristian Monzón")
        canvas.drawRightString(PAGE_W - 19 * mm, 11 * mm, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "h1":
            texto = flowable.getPlainText()
            clave = "s" + str(self.page) + "_" + str(self.seq.nextf("h1"))
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=0)
            self.notify("TOCEntry", (0, texto, self.page, clave))


story = []


def p(text, style="body"):
    story.append(Paragraph(text, ST[style]))


def h1(text):
    p(text, "h1")


def h2(text):
    p(text, "h2")


def bullet(text):
    p("• " + text, "bullet")


def table(headers, rows, widths=None):
    cells = [[Paragraph(escape(str(x)), ST["th"]) for x in headers]]
    cells.extend([[Paragraph(str(x), ST["td"]) for x in row] for row in rows])
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW]),
        ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL),
        ("LINEBELOW", (0, 1), (-1, -1), .35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([t, Spacer(1, 7 * mm)])


def newpage():
    story.append(PageBreak())


def flow_diagram():
    """Diagrama compacto del recorrido de una consulta ficticia."""
    d = Drawing(485, 93)
    cajas = [("Cliente", 0), ("API", 100), ("IA + KB", 200),
             ("Soporte", 300), ("Respuesta", 400)]
    for etiqueta, x in cajas:
        d.add(Rect(x, 30, 85, 42, rx=4, ry=4,
                   fillColor=PALE, strokeColor=TEAL, strokeWidth=1))
        d.add(String(x + 42, 48, etiqueta, textAnchor="middle",
                     fontName="Arial-Bold", fontSize=8.5, fillColor=TEAL_DARK))
        if x < 400:
            d.add(Line(x + 86, 51, x + 96, 51, strokeColor=TEAL, strokeWidth=1.3))
            d.add(Polygon([x + 96, 51, x + 92, 54, x + 92, 48],
                          fillColor=TEAL, strokeColor=TEAL))
    d.add(String(240, 12, "PostgreSQL: tickets, evidencia, traza, revisiones y correcciones",
                 textAnchor="middle", fontName="Arial", fontSize=8,
                 fillColor=GRAY))
    return d


# Portada
story.append(Spacer(1, 8 * mm))
p("PROYECTO INTEGRADOR · 2026", "subtitle")
p("SupportOps", "title")
p("Informe técnico del sistema local de atención asistida por IA", "subtitle")
story.append(Image(str(COVER), width=172 * mm, height=96 * mm))
p("Ilustración conceptual del flujo entre consulta, documentos y datos locales.", "caption")
story.append(Spacer(1, 12 * mm))
table(["Presentación", "Datos"], [
    ["Autores", "<b>Marco Medina</b> y <b>Cristian Monzón</b>"],
    ["Docente", "Alejandro Luis Bonavita"],
    ["Carrera", "Tecnicatura Superior en Ciencia de Datos e Inteligencia Artificial"],
    ["Institución", "ISFT N.º 197"],
    ["Año", "2026"],
], [43 * mm, 129 * mm])
p("Documento de entrega para demostración en una computadora Windows, con datos de una tienda ficticia y revisión humana de cada respuesta.", "small")
newpage()

# Índice dinámico
h1("Índice")
p("Las secciones describen el sistema local terminado. Las mediciones de H5 y recuperación corresponden a corridas históricas identificadas en el apartado de pruebas.")
toc = TableOfContents()
toc.levelStyles = [ST["toc1"]]
toc.dotsMinLevel = 0
story.append(toc)
newpage()

h1("1. Resumen ejecutivo")
p("SupportOps es un sistema local para una <b>tienda ficticia</b> con dos pantallas: cliente y soporte. El cliente consulta productos, compra sin pago, ve el seguimiento simulado y conversa con soporte. Las preguntas sencillas reciben una respuesta automática basada en datos de PostgreSQL; Ollama prepara propuestas privadas para casos complejos. El operador decide qué publicar.")
p("El proyecto reúne FastAPI, PostgreSQL, Streamlit, recuperación de conocimiento y un modelo de lenguaje ejecutado en la misma computadora. No necesita AWS, Docker ni mantener encendida otra PC. El repositorio de referencia es <link href='https://github.com/VynCrey/supportOps' color='#006F73'>github.com/VynCrey/supportOps</link>.")
h2("1.1 Resultado de la entrega")
table(["Componente", "Función en la demostración"], [
    ["Pantalla de cliente", "Tienda, pedidos con entrega estimada, chat persistente y adjuntos acotados de foto o PDF."],
    ["Pantalla de soporte", "Bandeja de chat, respuesta directa o propuesta privada, revisión humana y rectificación."],
    ["API y datos", "Persistencia local de productos, pedidos, fotos, mensajes, documentos, ejecuciones y decisiones."],
    ["Controles", "Reglas para respuestas simples, revisión de propuestas complejas, detección de secretos, negativa a extraer datos internos y tratamiento de adjuntos como no confiables."],
], [49 * mm, 123 * mm])
p("La palabra “terminado” se refiere al <b>prototipo académico local</b> descrito aquí. Los precios, clientes y compras son ficticios; no se conecta con pagos, mensajería ni bases de una empresa real. Esa frontera permite presentarlo completo y reproducible sin atribuirle una operación comercial que no realiza.")

h1("2. Problema, objetivo y caso de uso")
p("En una mesa de ayuda, una respuesta puede requerir identificar el problema, buscar instrucciones vigentes y comprobar que el texto no pida credenciales ni prometa acciones inexistentes. SupportOps ensaya ese circuito en un entorno controlado. El objetivo es <b>reducir trabajo de búsqueda y redacción sin quitar la decisión final al operador</b>.")
h2("2.1 Escenario ficticio")
p("La empresa de prueba se denomina <b>Tienda Faro</b>. El cliente ve ocho productos y registra compras sin pago. Para consultar o reclamar abre una conversación ligada a un ticket. Puede enviar más mensajes y soporte puede responder directamente o revisar una propuesta del agente. Si una respuesta se equivoca, el operador registra una rectificación y el cliente ve la versión vigente.")
h2("2.2 Reglas de aceptación")
bullet("La propuesta de IA no llega a la pantalla del cliente antes de una revisión humana.")
bullet("Cliente y soporte pueden continuar el mismo chat; el historial se conserva tras cerrar el navegador.")
bullet("La respuesta final queda vinculada a ticket, ejecución, revisión y, si corresponde, corrección posterior.")
bullet("Un pedido no consume dinero real; el inventario y los clientes son ficticios.")
bullet("Las consultas simples sobre precio o entrega se contestan con datos del producto o del pedido asociado; las demás se derivan a soporte.")
bullet("Una solicitud de datos internos masivos o una orden inyectada no se entrega al modelo como instrucción.")
h2("2.3 Antecedentes y objetivos")
p("El trabajo nació de prácticas de backend con Python y PostgreSQL. A esa base se sumaron una API, el flujo de agentes, recuperación de documentos, evaluación y pantallas de uso. No se declara una continuidad con el ejemplo de viajes que aparece en la plantilla institucional. El <b>objetivo general</b> es demostrar una atención ficticia asistida por IA, trazable y decidida por un operador. Los objetivos específicos son registrar casos, recuperar evidencia, redactar propuestas citadas, prevenir solicitudes inseguras y conservar revisiones y rectificaciones.")

h1("3. Arquitectura y componentes")
p("Las dos pantallas Streamlit consumen una API FastAPI que ejecuta consultas parametrizadas en PostgreSQL. El análisis usa un modelo local mediante Ollama, recupera documentos de la base de conocimiento y conserva la traza de los roles. Los programas se comunican solo por la interfaz local <b>127.0.0.1</b> en esta entrega.")
story.append(flow_diagram())
story.append(Spacer(1, 3 * mm))
table(["Capa", "Archivo o servicio", "Responsabilidad"], [
    ["Cliente", "cliente_app.py · puerto 8502", "Catálogo, compras simuladas y conversaciones con soporte."],
    ["Soporte", "streamlit_app.py · puerto 8501", "Chat, respuesta propia, propuesta de IA, revisión y métricas."],
    ["API", "main.py / run.py · puerto 8000", "Validación de entradas, rutas HTTP y errores controlados."],
    ["Datos", "db.py / PostgreSQL", "Tablas relacionales y trazabilidad de ejecuciones."],
    ["IA", "analysis.py / Ollama", "Triage, plan de búsqueda, borrador y supervisión."],
    ["Conocimiento", "retrieval.py / kb.json", "Recuperación léxica, por categoría e híbrida."],
], [30 * mm, 52 * mm, 90 * mm])
h2("3.1 Recorrido de una consulta")
p("Cliente → conversación ligada a un ticket → respuesta automática acotada si hay datos suficientes. En otro caso: propuesta local → búsqueda documental → borrador con citas → controles de seguridad → revisión del operador → respuesta visible al cliente. Un reclamo por daño pide foto y queda abierto. Cada análisis guarda resultado y traza; los borradores internos no se publican.")

h1("4. Datos y base PostgreSQL")
p("PostgreSQL conserva las relaciones y permite filtrar, contar y auditar sin depender de la memoria del navegador. El esquema tiene catorce tablas, incluidas mensajes, fotos y preparación de borradores. Cada pedido registra una entrega estimada ficticia. <b>bootstrap.py</b> crea la muestra y <b>run.py</b> aplica el esquema al arrancar, también sobre bases existentes. El catálogo viene de <b>catalogo_demo.json</b>; repetir la carga no repone el stock consumido.")
table(["Grupo", "Tablas y uso"], [
    ["Operación", "clientes, tickets y eventos: quién consulta, qué ocurrió y cuándo."],
    ["Conocimiento", "documentos y relaciones: procedimientos y enlaces para recuperación."],
    ["IA y decisiones", "ejecuciones, revisiones y correcciones: salida del agente, decisión inicial y versiones posteriores."],
    ["Tienda ficticia", "productos, pedidos, reclamos, mensajes_reclamo, fotos_reclamo y borradores_pendientes."],
], [41 * mm, 131 * mm])
h2("4.1 Muestras y conjuntos de evaluación")
table(["Conjunto", "Cantidad", "Finalidad"], [
    ["Arranque", "3 clientes · 6 tickets · 18 eventos · 8 productos", "Abrir la demostración en una instalación nueva."],
    ["Volumen sintético", "Hasta 500 clientes · 20.000 tickets · 60.000 eventos", "Probar consultas y hacer EDA; no representa demanda real."],
    ["KB", "56 documentos · 92 relaciones", "Respaldar propuestas y probar recuperación."],
    ["H5", "20 tickets reservados", "Comparar categoría, evidencia y decisión de una versión medida."],
], [36 * mm, 58 * mm, 78 * mm])
p("Los 20.000 tickets pertenecen a la <b>base local</b> donde se ejecutó generar_datos.py; no están dentro del ZIP ni de GitHub. Los 20 casos H5 son un conjunto aparte, definido en docs/eval/tickets_h5.csv. La instalación de la netbook crea su propia base ficticia.")

h1("5. Pantalla del cliente")
p("La vista de Tienda Faro presenta el catálogo, el precio y la disponibilidad ficticios. El cliente de prueba puede elegir un producto y registrar un pedido; el sistema reduce el stock dentro de una transacción y guarda el precio de ese momento. En “Mis pedidos” ve solo los pedidos del cliente seleccionado.")
p("En “Ayuda” puede iniciar un caso asociado a un pedido o producto y adjuntar una foto o PDF acotado. Ese primer mensaje crea un ticket; los siguientes continúan el mismo chat. El chat muestra respuestas automáticas claramente identificadas o mensajes publicados por soporte, nunca borradores privados. Un mensaje nuevo reabre el caso. Tras una rectificación se muestra la respuesta vigente.")
h2("5.1 Ejemplo de uso")
table(["Paso", "Acción", "Resultado"], [
    ["1", "Elegir Cliente demo 2 y revisar un producto.", "Se muestran datos del catálogo ficticio."],
    ["2", "Comprar una unidad (simulado).", "Se registra un pedido sin cobrar."],
    ["3", "Preguntar “¿Cuándo llega mi pedido?”.", "Responde con fecha y estado ficticios del pedido."],
    ["4", "Reclamar “Llegó en mal estado” y adjuntar foto.", "El asistente pide foto y soporte recibe el caso."],
    ["5", "Soporte revisa y publica una propuesta.", "El cliente ve solo la respuesta aprobada o corregida."],
], [16 * mm, 70 * mm, 86 * mm])
p("La selección del cliente en esta pantalla sirve para la <b>simulación local</b>; no constituye una identidad autenticada para un servicio público.")

h1("6. Pantalla de soporte")
p("El operador dispone de Bandeja, Productos y pedidos, Resumen, Análisis y revisión y Tickets. En Bandeja lee los mensajes y fotos, ve la propuesta privada cuando está lista y puede aprobarla, editarla o rechazarla con motivo. También puede responder directamente. La vista técnica muestra categoría, decisión, citas y evidencia.")
h2("6.1 Decisión y corrección")
table(["Acción", "Efecto"], [
    ["Aprobar", "Publica el texto del borrador después de escribir un motivo real."],
    ["Editar", "Requiere una respuesta corregida y motivo; publica el texto humano."],
    ["Rechazar", "No publica respuesta. Es la única opción para un análisis bloqueado."],
    ["Responder directo", "Publica un mensaje escrito por el operador, sin pasar por IA."],
    ["Corregir después", "Agrega una nueva versión con operador y motivo; conserva la revisión anterior."],
], [46 * mm, 126 * mm])
p("La revisión inicial es única por ejecución: una segunda llamada devuelve HTTP 409. Si el chat cambió tras el análisis, se exige analizar de nuevo. Las correcciones conservan la versión anterior para auditoría y muestran la nueva al cliente. Una respuesta deja el ticket resuelto; otro mensaje del cliente lo reabre. Cada cambio genera un evento.")

h1("7. Agente y base de conocimiento")
p("El análisis se divide en cuatro roles. <b>Triage</b> clasifica y señala datos faltantes. <b>Conocimiento</b> elige una búsqueda léxica, por categoría o híbrida. <b>Borrador</b> propone un texto y cita únicamente IDs de la evidencia entregada. <b>Supervisor</b> revisa respaldo y seguridad. Un control de código aplica reglas adicionales antes de permitir que el operador publique una respuesta.")
h2("7.1 Documentos y citas")
p("La base documental inicial contiene 56 piezas con identificadores KB-###. Para reclamos asociados a un producto, el análisis añade una ficha CAT-PR-### con datos actuales de ese producto y del pedido simulado. Si el reclamo no señala un producto, agrega CAT-CATALOGO con los ocho productos públicos. No expone la lista de clientes ni pedidos ajenos al modelo. El borrador solo puede citar IDs presentes en la evidencia de esa ejecución; una cita inventada bloquea la salida.")
h2("7.2 Límites de la generación")
p("El modelo produce propuestas, no garantías de exactitud. Puede confundir categorías o redactar algo incompleto. Recibe el último mensaje y hasta ocho mensajes recientes del mismo chat; ninguna propuesta interna entra en ese contexto. Las consultas simples de precio y seguimiento usan reglas y datos comprobados, sin modelo. Ante daño, el sistema pide foto y la propuesta permanece privada para revisión humana.")

h1("8. Seguridad y límites de datos")
p("Los controles se aplican en varias capas: validación de entradas, respuesta automática limitada a datos propios o públicos, búsqueda acotada, esquema de citas, detector de secretos y decisión humana para propuestas complejas. El agente no tiene una herramienta para volcar tablas completas. Las consultas para obtener la base, clientes, chats ajenos o todos los mensajes, y las órdenes para ignorar instrucciones, se apartan del modelo y pasan a revisión humana.")
h2("8.1 PDF como dato no confiable")
p("La pantalla del cliente acepta PDF de texto de hasta <b>2 MB y 5 páginas</b>. Extrae como máximo 2.500 caracteres, no conserva el archivo y no ejecuta contenido. Rechaza archivos cifrados, ilegibles o con formularios, enlaces, adjuntos o acciones activas. El texto se etiqueta como adjunto no confiable. Las instrucciones que intenten cambiar el comportamiento del agente se tratan como parte del reclamo y pasan a revisión, no como órdenes del sistema.")
h2("8.2 Foto del producto")
p("Ante daño o mal estado, el asistente pide una foto y deja el caso abierto. Se aceptan JPG y PNG pequeños. Pillow recodifica la imagen a JPEG y descarta metadatos antes de guardarla en la base local; soporte puede verla. La foto no se envía al modelo ni prueba por sí sola la causa o una garantía. Cuando está adjunta, se prepara un borrador privado para el operador.")
h2("8.3 Protección operativa")
bullet("No solicitar contraseñas, tokens ni códigos de verificación; los pedidos directos se detectan en texto, preguntas y faltantes.")
bullet("No afirmar pagos, envíos, desbloqueos o reembolsos no verificados por la base de datos.")
bullet("No mostrar el borrador crudo al cliente ni enviar mensajes por WhatsApp o correo.")
bullet("Mantener la instalación en localhost. La interfaz de demostración no incluye autenticación ni autorización para Internet y no debe exponerse públicamente.")
p("La revisión humana es un control efectivo de publicación, pero no reemplaza una evaluación de seguridad para un despliegue real. PostgreSQL y Ollama se ejecutan localmente; las contraseñas de la base no se guardan en el repositorio.")
h2("8.4 Riesgos y recursos")
table(["Recurso o riesgo", "Tratamiento en el proyecto"], [
    ["Procesador y memoria", "El modelo local puede tardar en una netbook; se usa una variante de 3B y una consulta por vez."],
    ["Dependencia de PostgreSQL y Ollama", "La preparación comprueba instalación y la API comunica fallas de disponibilidad."],
    ["Datos sensibles", "Los ejemplos son ficticios; el PDF y el chat advierten sobre datos no confiables y no se publican contraseñas."],
    ["Error de recuperación", "Citas visibles, control automático y decisión del operador antes de mostrar al cliente."],
], [50 * mm, 122 * mm])

h1("9. Pruebas y resultados")
p("La revisión automatizada del <b>27/11/2026</b> ejecutó <b>69 pruebas: 69 correctas</b>. Incluye análisis, recuperación, catálogo, PDF, fotos, chat y respuestas automáticas acotadas. Una integración aislada con PostgreSQL recorrió pedido, entrega estimada, respuesta automática, daño, foto y borrador privado; también se comprobó la migración desde el esquema anterior. La base real del usuario no se tocó. Estas verificaciones no prueban el acierto del modelo en todas las preguntas posibles.")
h2("9.1 Evaluación histórica H5")
p("La corrida H5 del <b>27/10/2026</b> evaluó 20 tickets reservados sobre una versión anterior. Acertó la categoría en 14/20, obtuvo evidencia aceptable o abstención correcta en 9/20, y una decisión automática dentro del rango esperado en 17/20. Los tres criterios se cumplieron juntos en <b>7/20</b>. Algunos borradores de esos siete también requerían corrección humana. T01 y T02 se rechazaron; T03 se aprobó; T20 se editó. Los registros permanecen en docs/eval/h5_v2.md y su CSV.")
h2("9.2 Recuperación documental")
table(["Método", "Hit@3", "MRR@3", "Lectura"], [
    ["Léxico", "7/15", "0,38", "Falla con sinónimos de este conjunto."],
    ["Grafo", "8/15", "0,38", "Depende de la categoría y del orden de documentos."],
    ["Híbrido", "8/15", "0,42", "Mejora la posición media, no la cobertura."],
], [33 * mm, 23 * mm, 23 * mm, 93 * mm])
p("Estas cifras corresponden a una KB de 56 documentos y 20 consultas fijadas antes de medir. H5 y recuperación <b>no se presentan como una nueva medición de la tienda</b>. La versión final añadió interfaz, catálogo y controles; una evaluación nueva con usuarios ficticios sería una medición distinta.")
h2("9.3 Fallas controladas")
p("Las pruebas del proyecto verifican, entre otros casos, HTTP 409 al revisar dos veces, 422 para un motivo de ejemplo, 503 si el modelo o la KB no están disponibles y 502 si la salida del análisis es inválida. Los fallos de modelo no se guardan como ejecuciones válidas inventadas.")

h1("10. Instalación y demostración en netbook")
p("La copia portable requiere Windows de 64 bits, Python 3.11, PostgreSQL y Ollama. El archivo requirements.txt instala FastAPI, psycopg, Uvicorn, Streamlit, pypdf y Pillow; Ollama descarga <b>qwen2.5:3b</b>. La primera preparación requiere Internet para descargar bibliotecas y modelo. Después, la API, la base, el modelo y las dos interfaces corren en la netbook sin la computadora original.")
table(["Orden", "Archivo", "Qué hace"], [
    ["1", "01_PREPARAR_NETBOOK.cmd", "Crea el entorno, esquema y datos ficticios; carga KB y modelo."],
    ["2", "02_INICIAR_API.cmd", "Inicia FastAPI en 127.0.0.1:8000."],
    ["3", "03_ABRIR_PANEL.cmd", "Abre soporte en 127.0.0.1:8501."],
    ["4", "04_ABRIR_CLIENTE.cmd", "Abre la tienda ficticia en 127.0.0.1:8502."],
    ["5", "05_COMPROBAR_DEMO.cmd", "Comprueba API, catálogo, Ollama y ambas pantallas."],
], [20 * mm, 63 * mm, 89 * mm])
p("El paquete de archivos no contiene la base original, contraseñas ni pesos del modelo. La preparación reconstruye una base local de demostración. Los 20.000 tickets generados para análisis histórico no se trasladan automáticamente. El procedimiento completo está en LEEME_NETBOOK.md.")

h1("11. Alcance, límites y continuidad")
p("El proyecto queda cerrado como <b>demostración local supervisada</b>: dos pantallas, catálogo, compras simuladas, chat persistente, propuesta de IA con evidencia, respuesta del operador y rectificación registrada. La base es ficticia, y los resultados históricos permiten mostrar tanto aciertos como fallos del agente.")
table(["Límite explícito", "Consecuencia para el uso"], [
    ["Datos y compras ficticios", "No se realizan cobros, entregas ni consultas a una empresa real."],
    ["Modelo local de 3B", "Las respuestas pueden variar y requieren evaluación del operador."],
    ["Sin autenticación pública", "Uso confinado a localhost; no abrir puertos a Internet."],
    ["PDF de texto acotado", "Un documento escaneado sin texto o superior a los límites se rechaza."],
    ["Sin canal externo", "La respuesta se ve dentro de la pantalla del cliente; no sale por WhatsApp ni correo."],
], [54 * mm, 118 * mm])
p("Una adopción empresarial requeriría autorización de datos reales, cuentas y roles, protección del transporte, copias de seguridad, revisión de la KB, monitoreo y una evaluación nueva de calidad y seguridad. Esas condiciones son de otro entorno; no forman parte del alcance de la demostración entregada.")

h1("12. Organización del trabajo y fuentes")
p("<b>Cristian Monzón</b> desarrolló el backend, el flujo de agentes, el panel, las reglas de seguridad y la revisión humana. <b>Marco Medina</b> integró la base de conocimiento, las estrategias de búsqueda y las evaluaciones de recuperación y H5. El trabajo conjunto se registra en el historial del repositorio y sus pull requests. Este informe describe el resultado integrado sin atribuir métricas nuevas a una corrida anterior.")
h2("12.1 Aprendizajes integrados")
p("El proyecto aplicó modelado relacional, transacciones, API REST, validación, procesamiento de datos sintéticos, métricas de recuperación, evaluación de agentes y diseño de interfaces. La principal lección técnica fue separar la calidad del borrador de la decisión de publicación: una cita válida o una categoría acertada no prueban que la respuesta sea adecuada. El historial de correcciones permite mejorar la atención sin ocultar lo que ocurrió antes.")
h2("12.2 Evidencia reproducible")
table(["Referencia", "Contenido"], [
    ["Repositorio", "<link href='https://github.com/VynCrey/supportOps' color='#006F73'>https://github.com/VynCrey/supportOps</link>"],
    ["Código", "main.py, db.py, analysis.py, safety.py, tienda_respuestas.py, foto_guard.py, cliente_app.py, streamlit_app.py."],
    ["Datos", "schema.sql, catalogo_demo.json, kb.json, generar_datos.py."],
    ["Pruebas", "test_analysis.py, test_marco.py, test_tienda.py, test_chat.py, test_cliente_app.py y docs/eval/."],
    ["Instalación", "LEEME_NETBOOK.md y scripts numerados 01 a 05."],
], [37 * mm, 135 * mm])
p("La imagen de portada es una ilustración conceptual generada con IA y no una captura del sistema. Se conserva en docs/entrega_final/portada_ia.png. El informe usa los nombres de los autores y el año indicados para la presentación.", "small")
h2("12.3 Balance y mejoras posteriores")
p("SupportOps satisface el alcance de demostración local: el cliente puede iniciar un caso, el agente prepara una respuesta fundada, soporte decide y el cliente ve solo la versión revisada. La prueba H5 muestra por qué ese control humano es necesario. Para una versión externa serían prioritarios autenticación real, permisos por cliente, pruebas de carga y una nueva evaluación de respuestas sobre el catálogo y los reclamos. Estas mejoras no se confunden con funciones de la entrega local.")

Report(OUT).multiBuild(story)
print(OUT)
