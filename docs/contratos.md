# Contratos provisionales para la integracion

Estos nombres siguen la guia del proyecto. Marco y Cristian deben revisar juntos
un ejemplo real de cada rol antes de conectar los modulos.

## Datos del ticket que recibe el analisis

```json
{
  "id": 3,
  "texto": "La API devuelve error 401 con el token",
  "plan": "Enterprise",
  "prioridad": "alta"
}
```

`categoria_real` y `familia` sirven para evaluar datos sinteticos. No se envian
al modelo durante el analisis para evitar filtrar la respuesta esperada.

## Salidas de los cuatro roles

| Rol | Responsable | Campos obligatorios |
| --- | --- | --- |
| Triage | Cristian | `categoria` (texto), `consulta` (texto), `faltantes` (lista de textos) |
| Conocimiento | Marco | `herramienta` (`lexical`, `grafo` o `hibrido`), `consulta` (texto), `motivo` (texto) |
| Borrador | Cristian | `texto` (texto), `citas` (lista de IDs de documentos), `preguntas` (lista) |
| Supervisor | Marco | `decision` (`listo`, `revisar` o `bloquear`), `motivos` (lista) |

Ejemplos de forma (no son respuestas reales del modelo):

```json
{"categoria": "api", "consulta": "error 401 token vencido", "faltantes": ["hora del error", "entorno"]}
```

```json
{"herramienta": "lexical", "consulta": "error 401 token vencido", "motivo": "Hay un codigo de error concreto"}
```

```json
{"texto": "Necesito mas datos antes de indicar un procedimiento.", "citas": [], "preguntas": ["¿A que hora ocurrio el error?"]}
```

```json
{"decision": "revisar", "motivos": ["Falta evidencia documental"]}
```

El recuperador de Marco expone `retrieve(query, category, tool)` y devuelve una
lista de documentos con sus IDs y evidencia. Antes de integrarlo, ambos deben
acordar las claves exactas de cada documento y guardar ejemplos JSON que pasen
las validaciones.

## Base de datos

El esquema PostgreSQL usa los nombres `clientes`, `tickets`, `eventos`,
`documentos`, `relaciones`, `ejecuciones` y `revisiones`. Los planes son `Basic`,
`Pro` y `Enterprise`; los estados del proyecto final son `abierto` y `resuelto`.
La practica anterior usaba `basico`/`pro` y `cerrado`: sus datos no se mezclan
con esta base nueva.

## API disponible

- `GET /health`: comprueba la conexion a PostgreSQL.
- `GET /tickets?plan=Pro`: lista tickets; el filtro por plan es opcional.
- `GET /tickets/{id}`: devuelve el ticket y sus eventos, sin los campos
  `categoria_real` ni `familia`.
- `POST /tickets`: recibe `{"cliente_id": 2, "texto": "..."}` y crea un ticket.
- `GET /kpis`: cantidades totales, abiertas y resueltas.
- `GET /ejecuciones/{id}`: recupera un analisis guardado y su revision, si existe.
  Si una salida pide credenciales, agrega `alerta_seguridad` al consultarla.
- `POST /ejecuciones/{id}/revision`: recibe `decision` (`aprobar`, `editar` o
  `rechazar`), `texto_final` y `motivo`. Cada ejecucion admite una revision.
- `POST /tickets/{id}/analizar`: llama los cuatro roles, recupera evidencia,
  aplica el gate y guarda una ejecucion con su `ejecucion_id`.

El bootstrap no crea ejecuciones. Hasta que Marco incorpore `retrieval.py`, el
adaptador devuelve evidencia vacia y marca `base_conocimiento` como
`pendiente_de_marco`. No se inventan documentos ni respuestas del modelo.
