# Usar SupportOps en otra computadora con Windows

Esta copia funciona **sin la computadora original encendida**. Streamlit es la pantalla; FastAPI, PostgreSQL y Ollama corren localmente en la misma netbook. No necesita Docker, AWS, Git ni VS Code para usarla.

## Qué se copia

Copiá `SupportOps_netbook.zip` a la netbook y **extraé todo el ZIP** en una carpeta, por ejemplo `C:\SupportOps`. Ejecutá los archivos `.cmd` dentro de esa carpeta extraída, nunca desde la vista previa del ZIP. El paquete contiene el código, el esquema y la base de conocimiento ficticia.

Los dos informes para presentar están en `docs\entrega_final\` dentro del ZIP: `SupportOps_Informe_Tecnico_2026.pdf` y `SupportOps_Informe_Proyecto_Integrador_2026.pdf`.

La versión actual del ZIP se genera en la carpeta `proyectoFinal` con `python crear_paquete_netbook.py`. Si ya tenés una copia anterior en la netbook, reemplazá la carpeta extraída por esta versión antes de repetir `01_PREPARAR_NETBOOK.cmd`.

El ZIP no contiene la base PostgreSQL de la otra computadora, contraseñas, el entorno `.venv` ni el modelo de Ollama. Esos componentes se crean o instalan **una vez en la netbook**. La copia arranca con 3 clientes, 6 tickets, 8 productos y 56 documentos ficticios; no trae las ejecuciones y revisiones hechas en la computadora original. No hace falta cargar 20.000 tickets para mostrar el programa.

## 1. Instalar los tres programas necesarios

Usá los instaladores oficiales y después abrí una terminal nueva:

1. [Python 3.11 para Windows](https://www.python.org/downloads/windows/) de 64 bits. Elegí la serie **3.11**, que es la probada con este proyecto. Durante la instalación, activá la opción para agregar Python al `PATH` si aparece. Comprobá con `python --version` o `py -3.11 --version`.
2. [PostgreSQL 18 para Windows](https://www.postgresql.org/download/windows/), la versión probada con este proyecto. Instalá el servidor, dejá el puerto **5432**, elegí una contraseña para el usuario `postgres` y recordala. No uses la contraseña de la computadora original si preferís otra.
3. [Ollama para Windows](https://ollama.com/download/windows). Comprobá con `ollama --version`. El instalador inicial descargará después `qwen2.5:3b`, el modelo que usa este proyecto. Su archivo ocupa alrededor de 1,9 GB; la velocidad de análisis depende del hardware.

La primera preparación necesita conexión a Internet para las bibliotecas de Python y el modelo. El uso posterior de la API, el panel, PostgreSQL y el modelo es local.

## 2. Preparar SupportOps una sola vez

En la carpeta extraída, hacé doble clic en **`01_PREPARAR_NETBOOK.cmd`**. Este archivo:

1. Comprueba Python 3.11 y Ollama.
2. Crea `.venv` e instala `requirements.txt`.
3. Crea `supportops_final` y carga clientes, tickets y eventos ficticios. Pedirá la contraseña local de `postgres`.
4. Carga los documentos de `kb.json`. Pedirá la misma contraseña otra vez.
5. Descarga el modelo `qwen2.5:3b` con Ollama.

Esperá el mensaje **«Preparacion terminada»**. Si falla, leé el error de la ventana, corregí el problema y ejecutá el mismo archivo otra vez: la muestra y los documentos no se duplican. No compartas la contraseña por chat ni la guardes en el proyecto.

## 3. Abrir el programa cada vez que lo uses

1. Hacé doble clic en **`02_INICIAR_API.cmd`**. Ingresá la contraseña de PostgreSQL y dejá abierta esa ventana. Verificá en el navegador: <http://127.0.0.1:8000/health>. Debe aparecer `"estado": "ok"` y `"base": "conectada"`.
2. Hacé doble clic en **`03_ABRIR_PANEL.cmd`** y dejá abierta esa segunda ventana. Si Streamlit pide un correo la primera vez, podés presionar Enter. Abrí <http://127.0.0.1:8501>.
3. Hacé doble clic en **`04_ABRIR_CLIENTE.cmd`**. Abrí <http://127.0.0.1:8502> para la pantalla del cliente ficticio. Las tres ventanas deben quedar abiertas durante la demostración.
4. Hacé doble clic en **`05_COMPROBAR_DEMO.cmd`**. Debe mostrar `OK` para API, catálogo, Ollama y las dos pantallas. Si indica `FALTA`, seguí la instrucción que aparece en esa ventana y repetí la comprobación.

## Demostración de las dos pantallas

1. En la pantalla del cliente, elegí una de las tres cuentas de prueba, mirá **Tienda** y hacé una compra simulada. Los otros 500 clientes de la muestra estadística no aparecen en esta selección. No se cobra dinero real.
2. En **Mis pedidos**, mirá el estado y la fecha estimada ficticia. Tocá **Preguntar por este pedido** y escribí «¿Cuándo llega mi pedido?». El asistente local responde automáticamente con los datos de ese pedido, sin llamar a Ollama. No hay envío real.
3. Para probar un reclamo, escribí «La mochila llegó en mal estado» en **Ayuda**, vinculando la mochila o su pedido. El asistente pedirá una foto. Adjuntá un JPG o PNG de hasta 2 MB en el chat. La foto se guarda sin metadatos en la base local; soporte puede verla. También se admite un PDF de texto pequeño (2 MB, 5 páginas), tratado como dato no confiable y sin conservar el archivo original.
4. En la pantalla de soporte, abrí **Bandeja**, elegí la conversación y leé el chat. Para casos complejos se prepara una **Propuesta para revisar** privada. **Aprobar** o **editar** publica la respuesta en el chat del cliente; **rechazar** no la publica. Siempre escribí un motivo real. Si Ollama no está disponible, respondé manualmente en la caja inferior.
5. En la pantalla del cliente, tocá **Actualizar mensajes** para ver la respuesta. Podés continuar el intercambio; queda en PostgreSQL y sigue disponible tras cerrar el navegador.
6. Si soporte se equivoca, puede usar **Corregir este mensaje** en una respuesta escrita directamente. Para una propuesta publicada tras revisión de IA, usá **Análisis y revisión** → **Corregir una decisión anterior**. La versión anterior queda en el historial y la nueva aparece en el chat del cliente.

Para una prueba sencilla, el cliente puede escribir «Compré un auricular ficticio y no enciende». Soporte puede responder «¿Podés indicar el número de pedido? No compartas claves ni datos bancarios». El cliente puede contestar y soporte continuar o pedir una propuesta nueva a la IA.

Un ticket pasa a **resuelto** al publicar una respuesta. Si el cliente vuelve a escribir, pasa a **abierto**. Si se rechaza o se retira una respuesta por error, vuelve a **abierto**; la corrección posterior queda registrada como evento.

Las consultas que piden una extracción masiva de datos internos o contienen órdenes para cambiar las instrucciones del agente se separan del modelo y pasan a revisión humana. El programa corre solo en `127.0.0.1`; la selección de clientes es una simulación, no una autenticación para Internet.

Para terminar, presioná **Ctrl+C** en cada una de las tres ventanas: cliente, soporte y API.

La primera llamada al modelo puede tardar. Si el panel dice que la API no está disponible, comprobá que la ventana de `02_INICIAR_API.cmd` siga abierta y que `/health` responda.

## 4. Demostración con un cliente ficticio

1. En el panel, abrí **Resumen**: verás los tickets de muestra.
2. Abrí **Tickets** → **Crear ticket**. Elegí `Cliente demo 2` y escribí: `Necesito el comprobante de agosto para presentarlo en la contaduría`.
3. Tocá **Crear ticket**. El panel mostrará el nuevo ID.
4. Abrí **Análisis y revisión humana**. El ID recién creado debería estar precargado; comprobalo y tocá **Analizar ticket** una sola vez.
5. Revisá la categoría, los documentos consultados, el borrador y la decisión automática. En **Registrar revisión**, aprobá, editá o rechazá según lo que realmente produjo el modelo. Escribí un motivo concreto y guardá la revisión. Si la ejecución está bloqueada, solo se puede rechazar.

Esta sección de tickets de práctica no publica en una conversación. Si revisás un reclamo desde **Bandeja**, aprobar o editar sí publica la respuesta en el chat ficticio local. Como el modelo genera texto, sus respuestas pueden variar.

## 5. Varias consultas en una conversación

En **Ayuda**, abrí un chat existente y escribí otro mensaje. El análisis usa el último mensaje del cliente y el contexto reciente del mismo chat. Una consulta sencilla de precio o seguimiento obtiene una respuesta automática basada en datos ficticios. Las demás quedan para revisión de soporte. Si el modelo falla, el chat persiste y el operador puede responder manualmente. La respuesta no sale de esta computadora.

## Problemas frecuentes

- **No encuentra Python 3.11 u Ollama:** instalá el programa faltante y abrí una terminal nueva antes de repetir `01_PREPARAR_NETBOOK.cmd`.
- **No se conecta a PostgreSQL:** comprobá que el servidor esté iniciado, que use el puerto 5432 y que la contraseña del usuario `postgres` sea la de esta netbook.
- **Error 503 al analizar:** abrí Ollama y comprobá `ollama list`; debe aparecer `qwen2.5:3b`. Si falta, ejecutá `ollama pull qwen2.5:3b`.
- **El panel no conecta:** iniciá la API primero y comprobá `/health`.
- **El análisis es lento:** el modelo local puede usar el procesador. Mantené abiertas la API y las pantallas que estés usando; esperá el resultado sin volver a tocar «Analizar ticket».

Para detalles técnicos, pruebas y limitaciones, consultá el [README](README.md) y el [informe técnico final](docs/entrega_final/SupportOps_Informe_Tecnico_2026.pdf).
