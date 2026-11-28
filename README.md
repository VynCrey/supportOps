# SupportOps: API de soporte con PostgreSQL y agentes

Este repositorio contiene el proyecto final compartido por Cristian y Marco.
La carpeta local `backend-python-postgresql` contiene ejercicios de aprendizaje
y usa otra base de datos; no forma parte de este repositorio.

El [informe técnico final en PDF](docs/entrega_final/SupportOps_Informe_Tecnico_2026.pdf)
presenta la consigna institucional, el diseño técnico, las pruebas y sus límites,
las fuentes y las instrucciones de reproducción. La imagen de portada y el
generador del PDF están en `docs/entrega_final/`.

Para copiar el programa a otra computadora Windows y usarlo de forma local,
seguí [LEEME_NETBOOK.md](LEEME_NETBOOK.md). Incluye instalación inicial,
arranque de la API y las dos pantallas, y una demostración ficticia. En
**Ayuda** y **Bandeja**, cliente y soporte intercambian mensajes que se actualizan
solos en pantalla y quedan en PostgreSQL. La IA puede preparar una propuesta sobre el último mensaje y el
contexto reciente; el operador decide si publicarla. Las preguntas sencillas
sobre precio o seguimiento simulado se responden automáticamente con datos de
la base. Los casos ambiguos o delicados producen un borrador privado para soporte.
`crear_paquete_netbook.py` genera el ZIP en la carpeta `proyectoFinal` usando
solo archivos versionados y sin incluir contraseñas ni entornos locales.
Después de abrir API y ambas pantallas, `05_COMPROBAR_DEMO.cmd` verifica
catálogo, modelo local y las direcciones de las dos interfaces.

## Sistema local de demostración

- `schema.sql` define catorce tablas: las siete originales, productos, pedidos,
  reclamos, correcciones, mensajes, fotos y estado de preparación de borradores.
- `bootstrap.py` crea la base `supportops_final` y carga una muestra ficticia:
  3 clientes, 6 tickets y 18 eventos.
- `documentos` y `relaciones` se llenan con `cargar_kb.py` a partir de `kb.json`
  (56 documentos y 92 relaciones). Ver [docs/kb_y_recuperacion.md](docs/kb_y_recuperacion.md).
- `run.py` inicia la API local. Ya permite comprobar la conexion, listar tickets,
  consultar uno con sus eventos, crear tickets y ver cantidades por estado.
- `db.py` guarda ejecuciones, revisiones humanas, correcciones y mensajes con
  historial, además del catálogo, las compras simuladas y los reclamos.
- `analysis.py` coordina cuatro roles, comprueba las salidas, aplica el gate y
  guarda la ejecucion. `llm.py` llama al modelo local de Ollama.
- `knowledge_adapter.py` conecta con `retrieval.py` de Marco (lexical, grafo e
  hibrido sobre PostgreSQL). Si el archivo faltara, la evidencia es vacia y el
  resultado lo indica claramente.
- La API incluye analisis de tickets, consulta de ejecuciones y revision humana.
- `streamlit_app.py` ofrece una bandeja de soporte con el chat, fotos, borradores
  y decisión humana en el mismo recorrido. `cliente_app.py` tiene tres rutas:
  Tienda, Mis pedidos y Ayuda. El cliente nunca ve borradores internos.
- Cada pedido ficticio conserva una fecha estimada de entrega y muestra un
  estado simulado. `tienda_respuestas.py` contesta solo consultas simples
  respaldadas por ese pedido o por la ficha pública de un producto.
- Ante un producto dañado, el asistente pide una foto o una descripción del daño.
  Si el cliente dice que no tiene foto, la conversación sigue con lo que pueda describir. La imagen se
  recodifica sin metadatos, se guarda localmente en PostgreSQL y queda visible
  para soporte. No se envía al modelo. Al adjuntarla se prepara un borrador
  privado; si Ollama falla, el operador puede contestar manualmente.
- `run.py` aplica el esquema al arrancar; al actualizar una base existente,
  incorpora la tabla de mensajes y conserva los primeros textos y respuestas
  revisadas de reclamos previos sin duplicarlos.
- Los reclamos pueden incluir texto extraído de un PDF pequeño. El archivo no
  se guarda ni ejecuta. Las instrucciones dentro de consultas y PDF son datos
  no confiables; los pedidos de datos internos masivos pasan a revisión sin
  consultar al modelo.
- La selección de cuentas es solo para una demostración local: no autentica
  personas reales. La API escucha en `127.0.0.1` y nunca debe exponerse en
  Internet ni recibir datos reales sin agregar autenticación y permisos.
- `generar_datos.py` puede ampliar la muestra hasta 500 clientes, 20.000
  tickets y 60.000 eventos ficticios. No agrega documentos: esa parte corresponde
  a la base de conocimiento de Marco.
- `eda.py` imprime tres hallazgos descriptivos calculados sobre la base local;
  el SQL reproducible y las limitaciones estan documentados en `docs/`.

## Preparar en Windows

Desde esta carpeta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\bootstrap.py
```

`bootstrap.py` pide la contrasena local de PostgreSQL. No se guarda en archivos.
La primera ejecucion crea la base y la muestra. Las siguientes comprueban el
esquema y muestran los conteos sin volver a insertar la muestra.

Para usar el entorno de la practica mientras se prepara uno independiente:

```powershell
..\backend-python-postgresql\.venv\Scripts\python.exe .\bootstrap.py
```

Para ver los conteos y luego generar el volumen final:

```powershell
.\.venv\Scripts\python.exe .\generar_datos.py
.\.venv\Scripts\python.exe .\generar_datos.py --aplicar
.\.venv\Scripts\python.exe .\eda.py
```

La segunda orden agrega los datos dentro de una transaccion y confirma los
conteos antes de guardar. Una nueva ejecucion, si ya alcanzo el objetivo, no
duplica filas. Si agregaste tickets manualmente sin sus tres eventos, se detiene
para que revises esa diferencia. Hacelo sobre la base ficticia, no sobre datos
reales.
El generador usa semilla 42, 18 familias y 54 frases base. La
[ficha de datos](docs/ficha_datos.md) explica origen, fechas y limites. `eda.py`
lee la base y calcula los hallazgos; no inventa resultados antes de ejecutarse.

## Cargar la base de conocimiento

Despues de `bootstrap.py`, una vez (se puede repetir sin duplicar):

```powershell
.\.venv\Scripts\python.exe .\cargar_kb.py
```

Pide la contrasena y carga los documentos y relaciones de `kb.json`. `run.py`
deja esa misma contrasena en `PGPASSWORD`, solo dentro de su proceso, para que
`retrieval.py` pueda leer la base durante el analisis.

## Probar la API

Detene cualquier servidor anterior con Ctrl+C. Desde esta carpeta ejecuta:

```powershell
.\.venv\Scripts\python.exe .\run.py
```

Ingresa la contrasena cuando se solicite. Luego abre:

- <http://127.0.0.1:8000/health> para comprobar la conexion.
- <http://127.0.0.1:8000/tickets?plan=Pro> para ver tickets de clientes Pro.
- <http://127.0.0.1:8000/tickets/3> para ver un ticket y sus eventos.
- <http://127.0.0.1:8000/kpis> para ver los conteos.
- <http://127.0.0.1:8000/docs> para probar los endpoints desde el navegador.

`GET /tickets` devuelve hasta 50 filas por pagina. Usa `limit` (1 a 200) y
`offset` para avanzar; `cantidad` es el total que coincide con el filtro.
`GET /clientes` lista los clientes para crear tickets. Tambien podes consultar
`GET /tickets/{id}/ejecuciones` para encontrar los IDs de analisis anteriores.

Cuando el analisis produzca ejecuciones, tambien estaran disponibles
`GET /ejecuciones/{id}` y `POST /ejecuciones/{id}/revision`. Una revision puede
aprobar, editar o rechazar; un borrador bloqueado solo admite rechazo. Una
segunda revision del mismo analisis se rechaza.
El `ejecucion_id` aparece al final de la respuesta de `POST /tickets/{id}/analizar`;
es el numero que se escribe en el campo de ruta para consultar o revisar esa
ejecucion. Si Swagger marca ese campo en rojo, la solicitud todavia no se envio.
Una regla adicional bloquea solicitudes de tokens, claves y contrasenas,
incluso al revisar una ejecucion creada antes de instalar esa regla.

`POST /tickets/{id}/analizar` necesita Ollama y el modelo `qwen2.5:3b` local.
Si faltan, responde 503 y no crea una ejecucion. Con la base de conocimiento
todavia vacia, la propuesta queda marcada para revision humana; no se presenta
como respuesta respaldada por documentos.

Las conversaciones usan `POST /reclamos` para abrir un caso,
`GET /reclamos/{ticket_id}/mensajes` para leerlo y los endpoints
`POST /reclamos/{ticket_id}/mensajes/cliente` y `/soporte` para continuar.
Una revisión aprobada o editada publica la respuesta en ese chat; el rechazo
no publica el borrador. Una corrección retira de la vista la versión anterior
y deja la nueva, con motivo e historial. Si la conversación cambia después
del análisis, la API exige analizarla de nuevo antes de aprobar o editar.
La selección de cliente y los endpoints de soporte son parte de una demo
local: no constituyen autenticación ni permisos para ofrecer el servicio en
Internet o con datos reales.

Para preparar el modelo en Windows, instala Ollama desde su
[pagina oficial](https://ollama.com/download/windows). Abre una terminal nueva
y ejecuta:

```powershell
ollama pull qwen2.5:3b
ollama list
```

Despues reinicia `run.py` y usa `POST /tickets/3/analizar` desde `/docs`.
La primera llamada puede demorar; el modelo responde cuatro veces, una por rol.

## Abrir el panel

Mantene la API corriendo y, en otra terminal dentro de esta carpeta, ejecuta:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\streamlit_app.py
```

Abri <http://localhost:8501>. El panel se conecta por defecto a la API local
en `http://127.0.0.1:8000`. Desde ahi podes ver cantidades, consultar o crear
tickets, analizar uno y registrar una revision. El panel selecciona los IDs de
ejecucion por vos. Si cambias el puerto de la API, configura la variable de
entorno `SUPPORTOPS_API_URL` antes de iniciar el panel.

Los planes de esta base se escriben `Basic`, `Pro` y `Enterprise`. Crear un
ticket por POST requiere un `cliente_id` existente y un texto de 10 a 4000
caracteres. El nuevo ticket inicia en estado `abierto`.

## Comprobar cambios

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p 'test_*.py' -v
```

Las pruebas unitarias no requieren una base de datos ni Ollama. Para probar el
flujo real se necesita PostgreSQL, la muestra cargada y Ollama con el modelo.

En la máquina de Cristian, el intérprete está en
`..\backend-python-postgresql\.venv\Scripts\python.exe`; reemplazá
`.\.venv\Scripts\python.exe` por esa ruta en los comandos anteriores.

La evaluación H5 de 20 tickets está en [docs/eval/h5_v2.md](docs/eval/h5_v2.md).
El [informe técnico final](docs/entrega_final/SupportOps_Informe_Tecnico_2026.pdf)
resume el funcionamiento, las pruebas y los límites de esta entrega. H5 quedó
documentada con 7/20 casos que cumplen sus tres criterios en una versión
anterior; esto no certifica que los borradores sean seguros para clientes.
Para recuperar los resultados de ejecuciones ya guardadas, o continuar solo los
casos pendientes sin crear tickets duplicados, ejecutá `evaluar_h5_local.py`
con la API local abierta. El script registra resultados automáticos; las
revisiones humanas se guardan desde el panel.

Los 20.000 tickets del análisis histórico requieren ejecutar el generador en
cada instalación si se desea repetir ese volumen; la demostración en la netbook
funciona con la muestra pequeña. No se incluye un volcado de la base en Git.
La evaluación H5 corresponde a una
versión anterior a los últimos ajustes del filtro de secretos; hay que repetirla
con el modelo real para medir esos cambios. El sistema sigue siendo un prototipo
local con revisión humana obligatoria.

## Documentación de integración

El [contrato inicial](docs/contratos.md) y la [entrega inicial a Marco](docs/entrega_marco.md)
conservan el acuerdo de trabajo de esa etapa. El estado actual está resumido en
el [informe técnico final](docs/entrega_final/SupportOps_Informe_Tecnico_2026.pdf).
