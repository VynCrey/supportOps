# SupportOps: API de soporte con PostgreSQL y agentes

Este repositorio contiene el proyecto final compartido por Cristian y Marco.
La carpeta local `backend-python-postgresql` contiene ejercicios de aprendizaje
y usa otra base de datos; no forma parte de este repositorio.

## Estado actual

- `schema.sql` define las siete tablas del proyecto en PostgreSQL.
- `bootstrap.py` crea la base `supportops_final` y carga una muestra ficticia:
  3 clientes, 6 tickets y 18 eventos.
- `documentos` y `relaciones` quedan vacias hasta incorporar el trabajo de Marco.
- `run.py` inicia la API local. Ya permite comprobar la conexion, listar tickets,
  consultar uno con sus eventos, crear tickets y ver cantidades por estado.
- `db.py` guarda ejecuciones de analisis y una revision humana por ejecucion.
  La API permite consultar ambas cuando existan.
- `analysis.py` coordina cuatro roles, comprueba las salidas, aplica el gate y
  guarda la ejecucion. `llm.py` llama al modelo local de Ollama.
- `knowledge_adapter.py` conecta con `retrieval.py` de Marco cuando exista.
  Mientras falte, la evidencia es vacia y el resultado lo indica claramente.
- La API incluye analisis de tickets, consulta de ejecuciones y revision humana.
- Esta muestra permite probar contratos e integracion. Aun no cumple el volumen
  final de 500 clientes, 20.000 tickets y 60.000 eventos de la guia.

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

Para preparar el modelo en Windows, instala Ollama desde su
[pagina oficial](https://ollama.com/download/windows). Abre una terminal nueva
y ejecuta:

```powershell
ollama pull qwen2.5:3b
ollama list
```

Despues reinicia `run.py` y usa `POST /tickets/3/analizar` desde `/docs`.
La primera llamada puede demorar; el modelo responde cuatro veces, una por rol.

Los planes de esta base se escriben `Basic`, `Pro` y `Enterprise`. Crear un
ticket por POST requiere un `cliente_id` existente y un texto de 10 a 4000
caracteres. El nuevo ticket inicia en estado `abierto`.

## Comprobar cambios

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p 'test_*.py' -v
```

Las pruebas unitarias no requieren una base de datos ni Ollama. Para probar el
flujo real se necesita PostgreSQL, la muestra cargada y Ollama con el modelo.

Esta API es una etapa del proyecto final. Aun faltan la base documental,
la recuperacion de Marco, la interfaz y el volumen final de datos. Los roles
necesitan mas pruebas con el modelo real antes de evaluar su calidad.

## Contrato de integracion

Ver [docs/contratos.md](docs/contratos.md). Marco y Cristian deben acordar
cualquier cambio de nombres o tipos antes de conectar sus modulos.
Para incorporarse al trabajo, ver [docs/entrega_marco.md](docs/entrega_marco.md).
