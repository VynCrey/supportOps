# Usar SupportOps en otra computadora con Windows

Esta copia funciona **sin la computadora original encendida**. Streamlit es la pantalla; FastAPI, PostgreSQL y Ollama corren localmente en la misma netbook. No necesita Docker, AWS, Git ni VS Code para usarla.

## Qué se copia

Copiá `SupportOps_netbook.zip` a la netbook y **extraé todo el ZIP** en una carpeta, por ejemplo `C:\SupportOps`. Ejecutá los archivos `.cmd` dentro de esa carpeta extraída, nunca desde la vista previa del ZIP. El paquete contiene el código, el esquema y la base de conocimiento ficticia.

El ZIP no contiene la base PostgreSQL de la otra computadora, contraseñas, el entorno `.venv` ni el modelo de Ollama. Esos componentes se crean o instalan **una vez en la netbook**. La copia arranca con 3 clientes, 6 tickets y 56 documentos ficticios; no trae las ejecuciones y revisiones hechas en la computadora original. No hace falta cargar 20.000 tickets para mostrar el programa.

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
3. Para terminar, presioná **Ctrl+C** en cada una de las dos ventanas.

La primera llamada al modelo puede tardar. Si el panel dice que la API no está disponible, comprobá que la ventana de `02_INICIAR_API.cmd` siga abierta y que `/health` responda.

## 4. Demostración con un cliente ficticio

1. En el panel, abrí **Resumen**: verás los tickets de muestra.
2. Abrí **Tickets** → **Crear ticket**. Elegí `Cliente demo 2` y escribí: `Necesito el comprobante de agosto para presentarlo en la contaduría`.
3. Tocá **Crear ticket**. El panel mostrará el nuevo ID.
4. Abrí **Análisis y revisión humana**. El ID recién creado debería estar precargado; comprobalo y tocá **Analizar ticket** una sola vez.
5. Revisá la categoría, los documentos consultados, el borrador y la decisión automática. En **Registrar revisión**, aprobá, editá o rechazá según lo que realmente produjo el modelo. Escribí un motivo concreto y guardá la revisión. Si la ejecución está bloqueada, solo se puede rechazar.

La revisión se guarda en PostgreSQL **sin enviar ningún mensaje a un cliente**. Como el modelo genera texto, sus respuestas pueden variar; la demostración no garantiza una aprobación automática.

## 5. Simular varias consultas como una conversación

En el panel abrí **Simulación** y elegí un cliente ficticio. Escribí una pregunta como si fueras ese cliente. Tocá **Pedir propuesta a la IA** y, como operador, revisá la respuesta, las citas y los documentos. Podés **aprobar**, **editar** la respuesta o **rechazar** la propuesta, siempre con un motivo. Al guardar, escribí otra pregunta y repetí el ciclo tantas veces como quieras.

Cada pregunta crea un ticket y se analiza **por separado**: el modelo no recuerda los mensajes anteriores. La conversación que ves en pantalla se conserva solo mientras esa pestaña siga abierta; los tickets, análisis y revisiones sí quedan en PostgreSQL. La respuesta aprobada o editada aparece en el panel como simulación, pero no se envía fuera de la computadora. Si el sistema bloquea una propuesta, solo permite rechazarla.

## Problemas frecuentes

- **No encuentra Python 3.11 u Ollama:** instalá el programa faltante y abrí una terminal nueva antes de repetir `01_PREPARAR_NETBOOK.cmd`.
- **No se conecta a PostgreSQL:** comprobá que el servidor esté iniciado, que use el puerto 5432 y que la contraseña del usuario `postgres` sea la de esta netbook.
- **Error 503 al analizar:** abrí Ollama y comprobá `ollama list`; debe aparecer `qwen2.5:3b`. Si falta, ejecutá `ollama pull qwen2.5:3b`.
- **El panel no conecta:** iniciá la API primero y comprobá `/health`.
- **El análisis es lento:** el modelo local puede usar el procesador. Mantené las dos ventanas abiertas y esperá el resultado; no vuelvas a tocar «Analizar ticket» mientras procesa.

Para detalles técnicos, pruebas y limitaciones, consultá el [README](README.md) y el [informe de entrega](docs/informe_entrega.md).
