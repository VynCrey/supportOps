"""Genera el informe imprimible de SupportOps desde los datos verificados del repo."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "SupportOps_Informe_Proyecto_Integrador_2026.pdf"
LOGO = HERE / "logo_instituto.png"
COVER = HERE / "portada_ia.png"

NAVY = colors.HexColor("#132338")
BLUE = colors.HexColor("#1673B8")
CYAN = colors.HexColor("#31BDD0")
LIGHT = colors.HexColor("#EAF3F8")
PALE = colors.HexColor("#F4F8FB")
GRAY = colors.HexColor("#526173")
LINE = colors.HexColor("#C9D9E4")
GREEN = colors.HexColor("#15715A")
RED = colors.HexColor("#A9323A")

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

S = getSampleStyleSheet()
S.add(ParagraphStyle(name="TitleCustom", fontName="Arial-Bold", fontSize=25, leading=29, textColor=NAVY, spaceAfter=11))
S.add(ParagraphStyle(name="SubtitleCustom", fontName="Arial", fontSize=12.5, leading=17, textColor=BLUE, spaceAfter=10))
S.add(ParagraphStyle(name="SectionCustom", fontName="Arial-Bold", fontSize=16.5, leading=20, textColor=NAVY, spaceBefore=12, spaceAfter=9, keepWithNext=True))
S.add(ParagraphStyle(name="SubCustom", fontName="Arial-Bold", fontSize=10.8, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=5, keepWithNext=True))
S.add(ParagraphStyle(name="BodyCustom", fontName="Arial", fontSize=9.1, leading=13.4, textColor=NAVY, spaceAfter=7))
S.add(ParagraphStyle(name="SmallCustom", fontName="Arial", fontSize=7.7, leading=10.8, textColor=GRAY, spaceAfter=5))
S.add(ParagraphStyle(name="BulletCustom", fontName="Arial", fontSize=9.0, leading=13.3, leftIndent=12, firstLineIndent=-7, textColor=NAVY, spaceAfter=4))
S.add(ParagraphStyle(name="TableHeadCustom", fontName="Arial-Bold", fontSize=8, leading=10.5, textColor=colors.white))
S.add(ParagraphStyle(name="TableCellCustom", fontName="Arial", fontSize=8.0, leading=10.8, textColor=NAVY))
S.add(ParagraphStyle(name="TableCellSmallCustom", fontName="Arial", fontSize=7.3, leading=10, textColor=NAVY))
S.add(ParagraphStyle(name="CalloutCustom", fontName="Arial-Bold", fontSize=9.2, leading=13.5, textColor=NAVY))
S.add(ParagraphStyle(name="CaptionCustom", fontName="Arial", fontSize=7.6, leading=10.5, textColor=GRAY, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10))
S.add(ParagraphStyle(name="CoverMetaCustom", fontName="Arial", fontSize=9.5, leading=14, textColor=NAVY))

W, H = A4
LEFT = 48
RIGHT = 48
TOP = 73
BOTTOM = 52
CW = W - LEFT - RIGHT


def p(text: str, style: str = "BodyCustom") -> Paragraph:
    return Paragraph(text, S[style])


def safe(text: str) -> str:
    return escape(str(text))


class Rule(Flowable):
    def __init__(self, color=BLUE, width=CW, thickness=1.3):
        super().__init__()
        self.width = width
        self.height = 7
        self.color = color
        self.thickness = thickness

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 3, self.width, 3)


class Pipeline(Flowable):
    def __init__(self):
        super().__init__()
        self.width = CW
        self.height = 138

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.roundRect(0, 0, CW, 138, 8, fill=1, stroke=0)
        boxes = [
            ("Consulta", "ticket"),
            ("Triage", "categoría"),
            ("Búsqueda", "KB"),
            ("Borrador", "citas"),
            ("Supervisor", "y gate"),
            ("Operador", "revisión"),
        ]
        gap = 6
        bw = (CW - 28 - gap * 5) / 6
        for i, (a, b) in enumerate(boxes):
            x = 14 + i * (bw + gap)
            c.setFillColor(colors.HexColor("#254565") if i < 5 else colors.HexColor("#176F78"))
            c.roundRect(x, 49, bw, 55, 5, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Arial-Bold", 8.3)
            c.drawCentredString(x + bw / 2, 80, a)
            c.setFont("Arial", 7.4)
            c.drawCentredString(x + bw / 2, 65, b)
            if i < 5:
                c.setStrokeColor(CYAN)
                c.setLineWidth(1.2)
                x1 = x + bw + 1
                x2 = x + bw + gap - 1
                c.line(x1, 76, x2, 76)
                c.line(x2 - 3, 79, x2, 76)
                c.line(x2 - 3, 73, x2, 76)
        c.setFillColor(colors.HexColor("#CFEAF4"))
        c.setFont("Arial", 8.2)
        c.drawCentredString(CW / 2, 22, "FastAPI coordina · PostgreSQL guarda tickets y trazas · Ollama ejecuta el modelo local")


def header_footer(c, doc):
    c.saveState()
    # Las dimensiones son idénticas en todas las páginas, incluida la carátula.
    logo_w = 122
    logo_h = logo_w * 80 / 270
    c.drawImage(str(LOGO), W - RIGHT - logo_w, H - 54, width=logo_w, height=logo_h, mask="auto")
    c.setFont("Arial-Bold", 7.2)
    c.setFillColor(GRAY)
    c.drawString(LEFT, H - 31, "ISFT Nº 197  ·  PROYECTO INTEGRADOR FINAL")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.line(LEFT, H - 60, W - RIGHT, H - 60)
    c.line(LEFT, 39, W - RIGHT, 39)
    c.setFont("Arial", 7.1)
    c.setFillColor(GRAY)
    c.drawString(LEFT, 27, "SupportOps · Informe técnico · 2026")
    c.drawRightString(W - RIGHT, 27, f"Página {doc.page}")
    c.restoreState()


doc = BaseDocTemplate(
    str(OUT), pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
    topMargin=TOP, bottomMargin=BOTTOM, title="SupportOps — Proyecto Integrador Final 2026",
    author="Cristian Monzón y Marco Medina", subject="Informe técnico y evaluación de SupportOps",
)
frame = Frame(LEFT, BOTTOM, CW, H - TOP - BOTTOM, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates(PageTemplate(id="all", frames=[frame], onPage=header_footer))
story: list = []


def section(title: str, new_page: bool = False):
    if new_page:
        story.append(PageBreak())
    story.append(p(safe(title), "SectionCustom"))
    story.append(Rule())


def sub(title: str):
    story.append(p(safe(title), "SubCustom"))


def para(text: str, *, small: bool = False):
    story.append(p(text, "SmallCustom" if small else "BodyCustom"))


def bullet(text: str):
    story.append(p("• " + text, "BulletCustom"))


def table(headers: list[str], rows: list[list[str]], widths: list[float] | None = None, small=False):
    cell_style = "TableCellSmallCustom" if small else "TableCellCustom"
    data = [[p(safe(v), "TableHeadCustom") for v in headers]]
    data += [[p(v, cell_style) for v in row] for row in rows]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1, splitByRow=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, BLUE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
    ]))
    story.append(t)
    story.append(Spacer(1, 9))


def callout(text: str, tone="blue"):
    edge = BLUE if tone == "blue" else (RED if tone == "red" else GREEN)
    cell = p(text, "CalloutCustom")
    t = Table([[cell]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT if tone == "blue" else PALE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, 0), 3, edge),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))


def fit_image(path: Path, max_w: float, max_h: float):
    with PILImage.open(path) as im:
        w, h = im.size
    k = min(max_w / w, max_h / h)
    return Image(str(path), width=w * k, height=h * k)


# Carátula
story.append(Spacer(1, 24))
story.append(p("SupportOps", "TitleCustom"))
story.append(p("Agente local de soporte asistido por inteligencia artificial", "SubtitleCustom"))
story.append(Rule(CYAN, CW, 2))
story.append(Spacer(1, 12))
story.append(fit_image(COVER, CW, 305))
story.append(p("Ilustración conceptual generada con IA para esta carátula. El sistema real se documenta y evalúa en las páginas siguientes.", "CaptionCustom"))
story.append(Spacer(1, 7))
table(["ENTREGA", "DATOS"], [
    ["Institución", "Unidad Integral de Educación Técnico Profesional de Avellaneda · Instituto Superior de Formación Técnica Nº 197"],
    ["Carrera y espacio", "Tecnicatura Superior en Ciencia de Datos e Inteligencia Artificial · PP: Proyecto Integrador · 3ro 1ra, turno mañana"],
    ["Docente", "Alejandro Luis Bonavita"],
    ["Estudiantes / autores", "Marco Medina y Cristian Monzón"],
    ["Ciclo lectivo", "2026"],
], [130, CW - 130], small=True)
story.append(p("Prototipo académico con datos ficticios. Documento digital e imprimible.", "SmallCustom"))

section("Guía de lectura y localización de la entrega", new_page=True)
para("Este informe sigue los apartados de la plantilla <b>Proyecto Integrador Final</b> del ISFT Nº 197. Documenta lo implementado, las evidencias observadas y los límites de una simulación local. La versión del sistema considerada es <b>main al 28/10/2026</b>.")
table(["Elemento", "Dónde encontrarlo / cómo acceder"], [
    ["Código fuente y versión", "<link href='https://github.com/VynCrey/supportOps' color='#1673B8'>github.com/VynCrey/supportOps</link> · rama <b>main</b>. El historial Git conserva los cambios. El PDF acompaña esta entrega en <b>docs/entrega_final/</b>."],
    ["Instalación y uso", "<b>LEEME_NETBOOK.md</b> (guía de tres pasos en Windows), <b>README.md</b> (detalle técnico) y los iniciadores <b>01_PREPARAR_NETBOOK.cmd</b>, <b>02_INICIAR_API.cmd</b>, <b>03_ABRIR_PANEL.cmd</b>."],
    ["Datos y acceso", "<b>bootstrap.py</b> genera muestra ficticia; <b>kb.json</b> y <b>cargar_kb.py</b> cargan procedimientos. No se publican contraseñas, base local ni cuentas de clientes reales."],
    ["Evidencia y anexos", "<b>docs/eval/h5_v2.md</b>, <b>docs/eval/tickets_h5.csv</b>, <b>docs/eval/metricas.md</b>, <b>docs/eval/bandit.md</b>, <b>docs/pruebas.md</b>, <b>docs/capturas/</b> y <b>docs/ficha_datos.md</b>."],
], [129, CW - 129])
sub("Registro breve de hitos")
table(["Momento", "Cambio y evidencia"], [
    ["Base local", "Modelo de tickets, eventos y API con PostgreSQL; panel para análisis y revisión."],
    ["Integración de conocimiento", "Marco incorporó KB y recuperación; se cargaron 56 documentos y 92 relaciones."],
    ["H5 (27/10/2026)", "20 tickets reservados evaluados con versión posterior al PR #5; se conservaron resultados y fallos."],
    ["Versión de entrega", "Ajustes posteriores de seguridad y simulación de conversación; 54 pruebas unitarias correctas el 28/10/2026. H5 no se repitió con esta versión."],
], [110, CW - 110])
callout("Alcance demostrado: sistema local funcional para consultas ficticias y revisión humana. No hay envío automático a clientes ni despliegue de producción.")

section("1. Presentación del proyecto", new_page=True)
sub("Descripción general")
para("SupportOps es un prototipo de mesa de ayuda para una organización ficticia con clientes y tickets. Un operador crea o recibe una consulta; la IA clasifica el problema, propone una búsqueda en la base de conocimiento, redacta una respuesta con citas y evalúa si necesita revisión. La persona responsable decide si aprueba, edita o rechaza. La interfaz de simulación permite repetir este ciclo con varias preguntas de un cliente ficticio.")
sub("Problema y contexto")
para("En un soporte con procedimientos dispersos, un operador puede tardar en localizar el documento adecuado o responder sin respaldo. El proyecto explora si una base de conocimiento y agentes especializados ayudan a preparar borradores verificables. <b>El caso es simulado:</b> no se estudió una empresa real, no se midió ahorro de tiempo real y la aplicación no atiende clientes externos.")
sub("Antecedentes y continuidad")
para("El trabajo comenzó como práctica progresiva de Python backend y PostgreSQL: tablas, consultas, relaciones, scripts, API y panel. Cristian desarrolló el flujo de API, agentes, reglas de seguridad y revisión; Marco integró la base de conocimiento, búsqueda y evaluación de recuperación. El proyecto evolucionó mediante PR y sesiones de prueba registradas. No se declara una continuidad con una propuesta anterior de Gestión de Proyectos porque esa relación no consta en el repositorio.")
sub("Actores y necesidades")
table(["Actor", "Necesidad", "Respuesta del prototipo"], [
    ["Cliente ficticio", "Plantear un problema de soporte.", "Crear una consulta de prueba en el panel. Ningún mensaje se envía fuera de la computadora."],
    ["Operador", "Ver evidencia, borrador y riesgos antes de contestar.", "Panel con documentos recuperados, salida del análisis y decisión humana registrada."],
    ["Equipo de proyecto", "Reproducir fallos y comparar versiones.", "Trazas, CSV de H5, pruebas automáticas y documentos de evaluación."],
], [86, 165, CW - 251])
sub("Requisitos y estado verificable")
table(["ID", "Requisito", "Estado / verificación"], [
    ["R1", "Registrar tickets y consultar su estado.", "Implementado; API y panel, muestra local y pruebas."],
    ["R2", "Analizar con IA y consultar procedimientos.", "Implementado; Ollama + KB en PostgreSQL. Exactitud limitada según H5."],
    ["R3", "Mostrar fuentes y guardar traza.", "Implementado; documentos y ejecución persistidos."],
    ["R4", "Bloquear pedidos de secretos y exigir intervención humana.", "Implementado con reglas deterministas y pruebas; calidad del borrador no garantizada."],
    ["R5", "Aprobar, editar o rechazar una única vez.", "Implementado; H5 registra ejemplos de los tres tipos y caso 409."],
    ["R6", "Reproducirlo en otra Windows.", "Preparación automatizada; guía incluida. Falta validar en la netbook destino."],
], [30, 242, CW - 272], small=True)

section("2. Objetivos y alcance", new_page=True)
sub("Objetivo general")
para("Construir y evaluar un sistema local de soporte asistido por IA que transforme consultas ficticias en propuestas respaldadas por documentos, con control humano antes de considerar cualquier respuesta final.")
sub("Objetivos específicos")
bullet("Diseñar y consultar datos relacionales de clientes, tickets, eventos, documentos, ejecuciones y revisiones en PostgreSQL.")
bullet("Coordinar clasificación, búsqueda, borrador y supervisión con salidas estructuradas del modelo local.")
bullet("Recuperar evidencia de una KB versionada y mostrar sus identificadores al operador.")
bullet("Aplicar reglas de seguridad y permitir aprobación, edición o rechazo con motivo registrado.")
bullet("Medir recuperación y comportamiento de punta a punta con casos fijados antes de evaluar.")
bullet("Preparar una instalación autónoma en otra computadora Windows, sin depender de la PC original.")
sub("Qué incluye y qué queda fuera")
table(["Incluido en esta entrega", "Fuera del alcance actual"], [
    ["API FastAPI, panel Streamlit y modo Simulación; datos ficticios; modelo local Ollama; KB, búsquedas, trazas, revisión y scripts de instalación.", "Clientes reales, integración con correo/WhatsApp o CRM, respuesta automática, autenticación multiusuario, despliegue público, Docker o AWS."],
    ["Pruebas de código y evaluaciones H5 y de recuperación con limitaciones explícitas.", "Promesa de calidad para producción, SLA de empresa real, conversación con memoria entre mensajes y seguridad de un servicio público."],
], [CW / 2, CW / 2])
sub("Criterios de aceptación de la entrega")
para("Se considera demostrable el alcance si una instalación local permite crear un ticket ficticio, ver la propuesta y los documentos consultados, guardar una revisión humana y consultar la traza; si los errores de servicio e insumos inválidos tienen respuesta controlada; y si se entregan código, instrucciones, datos de prueba y resultados medidos. <b>Que la IA produzca respuestas correctas para cualquier caso no es un criterio que el prototipo haya alcanzado.</b>")
callout("Criterio operativo esencial: una respuesta se muestra al cliente ficticio solo dentro de la simulación después de la decisión del operador; no sale a un canal externo.")

section("3. Recursos, viabilidad y riesgos", new_page=True)
sub("Recursos usados")
table(["Recurso", "Uso y dependencia"], [
    ["Windows 64 bits + Python 3.11", "Ejecución de API, scripts, pruebas y panel. Biblioteca fijada en requirements.txt."],
    ["PostgreSQL 18, puerto 5432", "Almacenamiento relacional local de siete tablas; contraseña ingresada en terminal."],
    ["Ollama + qwen2.5:3b", "Inferencia local. Qwen2.5:3b es el modelo; Ollama es el programa que lo ejecuta. Descarga inicial aproximada de 1,9 GB."],
    ["FastAPI + Uvicorn", "Servicios HTTP locales, validación de solicitudes y documentación /docs."],
    ["Streamlit", "Pantalla para tickets, indicadores, análisis, revisión y simulación."],
    ["Git y repositorio GitHub", "Control de versiones y entrega del código; no son necesarios para usar el ZIP en la netbook."],
], [144, CW - 144])
para("La solución es viable como demostración local con espacio libre suficiente y recursos para el modelo. En la netbook de destino se informaron 16 GB de RAM, CPU AMD Ryzen 5 5600H y aproximadamente 299 GB libres; esto orienta la preparación, pero el rendimiento del modelo aún debe comprobarse allí. No se estiman costos monetarios porque no se contrataron servicios pagos para el prototipo.")
sub("Riesgos y mitigaciones")
table(["Riesgo", "Impacto", "Tratamiento actual / pendiente"], [
    ["Modelo indisponible o lento", "Análisis falla o demora.", "503, prueba con Ollama local; comprobar la netbook antes de exponer."],
    ["KB incompleta o documento equivocado", "Borrador sin respaldo útil.", "Citas y revisión; métricas muestran fallos, falta mejorar ranking."],
    ["Pedido de claves o información sensible", "Exposición de secretos.", "Reglas de bloqueo y rechazo obligatorio; no usar datos reales."],
    ["Error de clasificación/alucinación", "Respuesta inexacta.", "Supervisión y operador; H5 muestra que el control sigue siendo necesario."],
    ["Pérdida de entorno local", "No se reproducen ejecuciones previas.", "Código y KB versionados; ZIP reinicia muestra, no migra la BD original."],
], [127, 98, CW - 225], small=True)
sub("Uso responsable de datos e IA")
para("Clientes, tickets y documentos de demostración son ficticios. No se deben cargar nombres, contraseñas, tokens ni documentación privada de una empresa. Los borradores pueden equivocarse o citar material irrelevante; la revisión humana es una condición del flujo. Para una versión real harían falta consentimiento y gobierno de datos, controles de acceso, retención, auditoría, pruebas de seguridad y evaluación con casos representativos antes de cualquier envío externo.")

section("4. Diseño y desarrollo del agente", new_page=True)
sub("Arquitectura y recorrido de una consulta")
story.append(Pipeline())
story.append(p("Figura 1. Coordinación secuencial de los componentes. La persona cierra el proceso.", "CaptionCustom"))
para("El panel envía la solicitud a la API. FastAPI consulta PostgreSQL y llama a <b>analysis.py</b>. Primero el agente de <b>triage</b> clasifica la consulta y extrae faltantes. El agente de <b>conocimiento</b> elige un modo de búsqueda; <b>knowledge_adapter.py</b> usa <b>retrieval.py</b> para recuperar documentos. El <b>borrador</b> redacta texto, preguntas y citas usando esa evidencia. El <b>supervisor</b> emite una decisión; después, un filtro determinista verifica seguridad y consistencia. La ejecución y su traza se guardan en PostgreSQL. Finalmente el operador revisa el resultado en Streamlit.")
sub("Contratos y persistencia")
table(["Componente", "Entrada → salida / función"], [
    ["API y panel", "Ticket, ID o texto → consulta HTTP, vista y acción del operador. Endpoints de salud, tickets, KPI, análisis, ejecución y revisión."],
    ["Modelo local", "Prompts por rol → salidas estructuradas validadas con Pydantic. Un JSON inválido provoca error controlado 502."],
    ["Recuperación", "Consulta, categoría y herramienta → hasta tres documentos con ID, versión y texto. No inventa documentos si no hay evidencia."],
    ["Reglas de seguridad", "Borrador, faltantes y evidencia → revisión o bloqueo por secretos, citas inválidas o respuesta vacía."],
    ["PostgreSQL", "Almacena clientes, tickets, eventos, documentos, relaciones, ejecuciones y revisiones; estas últimas son únicas por ejecución."],
], [122, CW - 122])
sub("Decisiones de coordinación")
para("Se separaron cuatro tareas del modelo para que clasificación, recuperación, redacción y supervisión tengan entradas y salidas auditables. El filtro determinista se ejecuta además de la opinión del supervisor: la revisión del modelo por sí sola mostró errores en pruebas preliminares. Los IDs públicos de tickets se excluyeron de los prompts del modelo para evitar que los confundiera con IDs de la KB; las citas se validan contra documentos realmente recuperados.")

section("4.1 Datos, fuentes y recuperación", new_page=True)
sub("Modelo de datos")
para("El esquema <b>schema.sql</b> contiene siete tablas: clientes, tickets, eventos, documentos, relaciones, ejecuciones y revisiones. Las claves foráneas enlazan tickets con clientes, eventos con tickets y revisiones con ejecuciones. Las salidas del análisis y las trazas se guardan para reconstruir qué propuso el sistema. Los identificadores de los documentos de conocimiento siguen la forma KB-###.")
table(["Conjunto", "Origen y volumen", "Uso y límite"], [
    ["Muestra inicial", "bootstrap.py: 3 clientes, 6 tickets y 18 eventos ficticios.", "Permite abrir el panel después de instalar, sin datos empresariales."],
    ["Conjunto ampliado", "generar_datos.py: hasta 500 clientes, 20.000 tickets y 60.000 eventos.", "Sirve para volumen y EDA; frases repetitivas, sin validez externa."],
    ["Base de conocimiento", "kb.json: 56 documentos ficticios, 92 relaciones; cargar_kb.py los inserta en PostgreSQL.", "Procedimientos académicos y versiones. No representan políticas de una empresa real."],
    ["Evaluación H5", "20 tickets y criterios previstos en docs/eval/tickets_h5.csv.", "Casos reservados de la versión medida; no equivalen a tráfico de producción."],
], [96, 202, CW - 298], small=True)
sub("Cómo funciona la búsqueda aumentada con documentos")
para("Marco organizó la KB con categorías, versiones y relaciones. <b>cargar_kb.py</b> comprueba y carga el archivo; la búsqueda usa PostgreSQL. Hay tres estrategias: <b>léxica</b> (coincidencia de términos con TF-IDF), <b>grafo por categoría</b> y <b>híbrida</b> (combina rankings con Reciprocal Rank Fusion). El resultado devuelve hasta tres documentos al borrador. El sistema exige que las citas sean IDs de esa evidencia; si no hay documentos o la categoría es general, debe reconocer la falta de respaldo y pasar a revisión.")
para("El modo llamado ‘grafo’ de la recuperación actual prioriza documentos de la categoría por ID; no recorre aún las rutas causales por síntoma que se modelaron en <b>mi_grafo.py</b>. Esa diferencia explica parte de los fallos medidos y se informa como límite. El proceso no consulta Internet durante el análisis y no incorpora datos externos en tiempo real.")
sub("EDA sobre datos ficticios")
para("Una corrida de <b>eda.py</b> sobre el conjunto ampliado, antes de añadir H5, registró 12.001 tickets abiertos (60,0 %), mediana de 59 minutos a la primera respuesta y 205 minutos a resolución, sin inconsistencias de fecha/estado detectadas. Son propiedades del generador y de esa corrida. No se presentan como SLA ni comportamiento de clientes reales.")

section("4.2 IA, revisión y decisiones de implementación", new_page=True)
sub("Componente de inteligencia artificial")
para("El modelo <b>qwen2.5:3b</b> se ejecuta localmente con Ollama. Recibe una consulta concreta y contexto limitado, produce categoría, estrategia de búsqueda, borrador con citas y una evaluación. Las respuestas tienen variación entre corridas. La validación estructural rechaza formatos inesperados; una cita inexistente se bloquea. Si no existe evidencia suficiente, el sistema conserva la incertidumbre y solicita revisión, en lugar de dar por correcta una respuesta automática.")
sub("Revisión humana y seguridad")
para("El operador observa el texto, la categoría y los documentos. Puede <b>aprobar</b> (usar el borrador), <b>editar</b> (registrar una respuesta corregida) o <b>rechazar</b>. Debe escribir un motivo; el texto de ejemplo ‘string’ se rechaza. Una ejecución bloqueada por solicitud de credenciales solo ofrece rechazo. No se admite una segunda revisión de la misma ejecución (HTTP 409). Guardar la revisión no envía mensajes por red a un cliente.")
sub("Aportes y reutilización")
table(["Elemento", "Procedencia y adaptación"], [
    ["Práctica inicial de backend", "Ejercicios de Cristian en carpeta hermana backend-python-postgresql; base para SQL, Python y API. No es un framework externo del informe."],
    ["API, flujo de agentes y controles", "Implementación del equipo en main.py, analysis.py, safety.py, db.py y panel. Correcciones a partir de pruebas y revisiones."],
    ["KB y recuperación", "Integración de Marco: kb.json, cargar_kb.py, retrieval.py, knowledge_adapter.py, evaluación y documentación de la KB."],
    ["Bibliotecas y modelo", "FastAPI, psycopg, Streamlit, Ollama y Qwen2.5 son recursos externos identificados en requirements.txt y referencias oficiales."],
], [152, CW - 152])
sub("Elecciones relevantes")
bullet("PostgreSQL aporta relaciones, integridad y consultas necesarias para tickets y revisiones; la DB local no se incluye en Git.")
bullet("Ollama evita depender de una API remota para la demostración, con el costo de instalar el modelo y exigir hardware local.")
bullet("FastAPI separa servicio y presentación; Streamlit ofrece una interfaz rápida para un prototipo educativo.")
bullet("La simulación permite varias consultas, pero cada mensaje es un ticket nuevo e independiente: no hay memoria conversacional del modelo.")

section("5. Pruebas y resultados", new_page=True)
sub("Plan y fuentes de verificación")
para("Se usaron pruebas automatizadas de componentes, consultas de recuperación con respuestas esperadas, una evaluación de veinte tickets de punta a punta (H5) con casos normales y adversos, revisiones humanas guardadas y llamadas a la API ante fallas. Los casos H5 fueron definidos antes de la corrida y no se modificaron prompts, código ni KB entre tickets.")
table(["Escenario esperado", "Resultado observado", "Evidencia / observación"], [
    ["Consulta con procedimiento", "T03 recuperó KB-007, clasificó facturación y recibió revisión ‘aprobar’.", "H5 v2, ejecución 19 y captura. El borrador repetía parte del ticket; el registro se preserva tal como ocurrió."],
    ["Consulta sin detalle suficiente", "T13 quedó en revisión sin documento aceptable.", "H5 v2; no se presume respuesta completa."],
    ["Pedido inseguro", "T01 solicitó una clave y fue bloqueado; el operador rechazó.", "H5 v2, ejecución 15 y captura. El bloqueo funcionó, el borrador falló."],
    ["Búsqueda de dos problemas", "T20 recuperó cobro duplicado y una guía de SMS para avisos por correo; el operador editó.", "H5 v2, ejecución 36 y captura. No se afirmó un reembolso."],
    ["Falla de servicios / salida", "503 si modelo/KB no están disponibles; 502 ante salida inválida. También se observó 409 y 422.", "docs/pruebas.md y capturas; 502/503 verifican código y mensaje, no conteo de filas antes/después."],
], [141, 167, CW - 308], small=True)
sub("Pruebas del código actual")
para("El 28/10/2026 se ejecutó <b>python -m unittest discover -s . -p 'test_*.py' -q</b> con el entorno Python del proyecto: <b>54 pruebas correctas</b>. Comprueban contratos, seguridad, validación, KB, recuperación, API y simulación. Son pruebas rápidas con dobles en varios flujos: no sustituyen el uso real de PostgreSQL y Ollama. Las advertencias de contexto de Streamlit en la consola no hicieron fallar la suite.")

section("5.1 Indicadores cuantitativos", new_page=True)
sub("Evaluación H5 de veinte tickets")
table(["Indicador", "Cómo se midió", "Resultado"], [
    ["Categoría", "Coincidencia con categoría esperada del CSV.", "14/20 (70 %)"],
    ["Documento aceptable", "Al menos un ID aceptable o abstención prevista.", "9/20 (45 %)"],
    ["Decisión", "Dentro del rango previsto (listo/revisar/bloquear).", "17/20 (85 %)"],
    ["Tres criterios juntos", "Cumplimiento simultáneo de los tres anteriores.", "7/20 (35 %)"],
], [126, 235, CW - 361])
para("La corrida H5 se realizó el <b>27/10/2026</b> sobre la versión posterior al PR #5. Los siete casos con los tres criterios cumplidos fueron T03, T08, T13, T16, T17, T18 y T20. <b>No significa que sus borradores fueran seguros o listos para enviar:</b> T16 inventó información sobre cobros, T17 omitió advertir que no compartan el token y T18 no indicó escalar el incidente. Cuatro ejecuciones recibieron revisión humana registrada: T01 y T02 rechazadas, T03 aprobada y T20 editada. Los otros dieciséis casos no tienen esa revisión.")
callout("Validez temporal: H5 mide una versión anterior. Los cambios de seguridad posteriores tienen pruebas automáticas, pero no una nueva corrida H5 con el modelo real.", "red")
sub("Recuperación de documentos")
para("La evaluación de búsqueda fijó <b>20 consultas</b> (15 con respuesta esperada y 5 sin respuesta), KB de 56 documentos y corte en los tres primeros resultados. <b>Hit@3</b> significa que un documento aceptable apareció entre esos tres; <b>MRR@3</b> favorece que aparezca más arriba. Los denominadores de Hit@3 son las 15 consultas respondibles.")
table(["Estrategia", "Hit@3", "MRR@3", "Lectura"], [
    ["Léxica", "7/15 = 0,47", "0,38", "Falló en 5/5 consultas con sinónimos de este conjunto."],
    ["Grafo por categoría", "8/15 = 0,53", "0,38", "La abstención 5/5 en consultas sin respuesta usa categoría esperada conocida: techo optimista."],
    ["Híbrida", "8/15 = 0,53", "0,42", "Mejor posición media aquí, sin mejora de Hit@3 frente a grafo."],
], [108, 86, 72, CW - 266], small=True)
sub("Exploración de una política adaptativa")
para("Se probó un bandit contextual ε-greedy con 33 consultas de entrenamiento derivadas de títulos, 15 consultas respondibles de evaluación y cinco semillas. No superó a la mejor estrategia fija: empató en 0,53 o bajó a 0,47 según la semilla. El experimento queda como resultado negativo útil: con estos datos y señales no justifica sustituir el selector actual. Las condiciones están en <b>docs/eval/bandit.md</b>.")

section("5.2 Análisis de errores y límites", new_page=True)
sub("Qué se cumplió")
para("Se construyó el circuito técnico completo: entrada, clasificación, recuperación, borrador, validación, almacenamiento, visualización y decisión humana. Los casos HTTP y las pruebas automáticas cubren fallas previsibles. El informe y el repositorio permiten reproducir la demostración en una computadora Windows con servicios locales.")
sub("Qué no resolvió la evaluación")
bullet("La exactitud de H5 fue desigual: solo 7/20 reunieron categoría, evidencia y decisión dentro de lo esperado, y aun algunos de ellos tenían un borrador incorrecto.")
bullet("La búsqueda léxica no resolvió los sinónimos de la evaluación; el grafo por categoría puede priorizar documentos genéricos o antiguos frente a uno específico.")
bullet("T01 y T02, aunque mejoraron su clasificación después de cambios previos, mostraron borradores o evidencia que justificaron rechazo. La salida varía con el modelo.")
bullet("En H5, T05 y T12 se bloquearon por falsos positivos del detector de secretos. El filtro se corrigió posteriormente y se verificó con pruebas, sin repetir H5.")
bullet("El panel funciona como simulación local y no prueba escalabilidad en varios usuarios, seguridad de producción ni integración real con canales de soporte.")
sub("Pendientes dentro del prototipo y mejoras fuera del alcance")
table(["Corto plazo / evaluación", "Versión futura / uso real"], [
    ["Repetir H5 tras cambios y usar casos nuevos reservados; medir calidad del texto además de tres criterios estructurados; corregir ranking por síntomas y sinónimos.", "Autenticación, roles, protección de datos, auditoría, observabilidad, copias de seguridad, pruebas con usuarios y políticas reales autorizadas."],
    ["Verificar instalación y rendimiento en la netbook; conservar resultados y tiempos de esa máquina.", "Integración controlada con canales externos y eventual empaquetado/despliegue solo tras evaluación y controles."],
], [CW / 2, CW / 2])

section("6. Conclusiones", new_page=True)
sub("Balance del proyecto")
para("SupportOps responde al problema planteado como <b>prototipo académico supervisado</b>: organiza tickets ficticios, consulta una KB, propone respuestas y conserva las decisiones humanas. Su aporte más sólido es el flujo auditable, no una promesa de respuesta automática correcta. Las mediciones muestran deficiencias relevantes de clasificación, recuperación y redacción. El sistema debe seguir bajo revisión humana y no está listo para atender clientes reales.")
sub("Aprendizajes integrados")
para("El proyecto integró modelado relacional y SQL, Python backend, contratos HTTP, validación de datos, pruebas automatizadas, recuperación de información, evaluación de sistemas de IA, análisis exploratorio y control de versiones en equipo. La comparación entre resultados esperados y observados permitió distinguir un acierto estructural de una respuesta realmente útil y segura. La colaboración entre Cristian y Marco también exigió interfaces estables, revisión de PR y registro honesto de fallos.")
sub("Mejoras propuestas")
bullet("Usar efectivamente rutas por síntoma del grafo y ampliar el léxico de sinónimos, evaluándolo con consultas nuevas.")
bullet("Mejorar las instrucciones y validaciones del borrador para evitar repetir el ticket, prometer acciones inexistentes o mezclar problemas.")
bullet("Agregar métricas de seguridad y calidad del texto, con revisión humana ciega y comparación entre versiones del mismo conjunto reservado.")
bullet("Antes de datos reales, desarrollar identidad de usuarios, permisos, gestión de secretos, resguardo de datos y un mecanismo de publicación aprobado por el operador.")
callout("Conclusión: el proyecto demuestra una arquitectura funcional y medible. La evidencia sostiene una demostración local con clientes ficticios y revisión humana; no sostiene autonomía operativa.", "green")

section("7. Reproducción, bibliografía y anexos", new_page=True)
sub("Instalar y ejecutar en otra netbook Windows")
para("La entrega portable se copia mediante <b>SupportOps_netbook.zip</b>, se extrae por completo y se usa sin la PC original encendida. La netbook necesita instalar <b>Python 3.11 de 64 bits</b>, <b>PostgreSQL 18</b> y <b>Ollama</b>. Los paquetes FastAPI, psycopg, Uvicorn y Streamlit se instalan en un entorno virtual desde <b>requirements.txt</b>; el modelo descargado por Ollama es <b>qwen2.5:3b</b>. La descarga inicial requiere Internet, pero el uso posterior es local.")
table(["Orden", "Acción", "Comprobación"], [
    ["1", "Instalar los tres programas oficiales. Mantener PostgreSQL en puerto 5432 y recordar la contraseña local de postgres.", "python/py -3.11 --version, Ollama disponible y servidor PostgreSQL iniciado."],
    ["2", "Extraer ZIP. Ejecutar 01_PREPARAR_NETBOOK.cmd: crea entorno, instala requisitos, carga muestra y KB, descarga qwen2.5:3b.", "Mensaje ‘Preparacion terminada’; sin duplicar datos al repetir."],
    ["3", "Ejecutar 02_INICIAR_API.cmd y dejar la ventana abierta. Abrir 127.0.0.1:8000/health.", "‘estado’: ‘ok’ y ‘base’: ‘conectada’."],
    ["4", "Ejecutar 03_ABRIR_PANEL.cmd y abrir 127.0.0.1:8501.", "Panel con Resumen, Tickets, Análisis y Simulación."],
    ["5", "Crear consulta ficticia y pedir propuesta; revisar, editar/aprobar/rechazar con motivo.", "Resultado visible en el panel y revisión guardada localmente."],
], [38, 314, CW - 352], small=True)
para("El ZIP no contiene la base de datos de la PC original, contraseñas, entorno virtual ni pesos del modelo. Su preparación crea una base nueva con muestra ficticia: los tickets y revisiones anteriores no se trasladan. El paso a paso completo y la solución de problemas están en <b>LEEME_NETBOOK.md</b>. El curso no exige Docker ni AWS para esta demostración, y la entrega actual no los utiliza.")
sub("Fuentes oficiales para instalar y comprender las herramientas")
table(["Recurso", "Referencia"], [
    ["Python 3.11", "<link href='https://docs.python.org/3.11/using/windows.html' color='#1673B8'>docs.python.org/3.11/using/windows.html</link>"],
    ["PostgreSQL para Windows", "<link href='https://www.postgresql.org/download/windows/' color='#1673B8'>postgresql.org/download/windows/</link>"],
    ["Ollama / Qwen2.5:3b", "<link href='https://ollama.com/download/windows' color='#1673B8'>ollama.com/download/windows</link> · <link href='https://ollama.com/library/qwen2.5:3b' color='#1673B8'>ollama.com/library/qwen2.5:3b</link>"],
    ["FastAPI", "<link href='https://fastapi.tiangolo.com/' color='#1673B8'>fastapi.tiangolo.com</link>"],
    ["Streamlit", "<link href='https://docs.streamlit.io/get-started/installation/command-line' color='#1673B8'>docs.streamlit.io/get-started/installation/command-line</link>"],
], [141, CW - 141], small=True)

section("Anexos de evidencia y trazabilidad", new_page=True)
sub("Mapa de los archivos de verificación")
table(["Archivo / carpeta", "Contenido verificable"], [
    ["docs/eval/tickets_h5.csv", "Entradas T01–T20, expectativas, IDs, resultados y revisiones."],
    ["docs/eval/h5_v2.md", "Condiciones, cifras, errores y límite temporal de H5."],
    ["docs/eval/h5_observaciones.json", "Borradores, supervisión y observaciones de las ejecuciones medidas."],
    ["docs/eval/metricas.md", "Definición y resultados de Hit@3 / MRR@3 por estrategia."],
    ["docs/eval/bandit.md", "Experimento adaptativo, semillas, recompensa y resultado negativo."],
    ["docs/ficha_datos.md · docs/pruebas.md", "Origen sintético, EDA, HTTP y capturas de fallo."],
    ["test_*.py · requirements.txt", "Contratos automatizados y versiones de bibliotecas."],
], [181, CW - 181], small=True)
sub("Capturas de revisiones humanas")
para("Las capturas originales están en <b>docs/capturas/</b>. Se incluyen aquí ejemplos visuales reducidos. El registro completo se conserva en PostgreSQL local; las imágenes y el CSV respaldan los casos seleccionados de la sesión H5.")
for filename, caption in [
    ("h5_rechazar_T01.png", "Figura 2. T01: bloqueo por pedido de clave y rechazo humano."),
    ("h5_aprobar_T03.png", "Figura 3. T03: documento KB-007 y aprobación registrada."),
    ("h5_editar_T20.png", "Figura 4. T20: edición humana de la respuesta sobre cobro y avisos."),
]:
    path = ROOT / "docs" / "capturas" / filename
    if path.exists():
        story.append(fit_image(path, CW, 250))
        story.append(p(caption, "CaptionCustom"))

para("Este PDF fue elaborado a partir de la plantilla institucional, el código y los registros del repositorio. La ilustración de portada se generó con IA; el logo se extrajo de la presentación institucional entregada por los estudiantes y mantiene idéntica medida y proporción en todas las páginas.", small=True)


if __name__ == "__main__":
    doc.build(story)
    print(OUT)
