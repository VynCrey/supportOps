# Base de conocimiento y recuperación (parte de Marco)

## De dónde sale la KB

```
laboratorio de Marco (SQLite)  ──exportar_kb.py──▶  kb.json  ──cargar_kb.py──▶  PostgreSQL  ──retrieval.py──▶  analysis.py
     se edita y se mide                        se versiona en Git       documentos, relaciones       lexical / grafo / hibrido
```

La KB se edita y se mide en el laboratorio de Marco. `kb.json` es lo que se entrega: así el sistema integrado usa la misma KB sobre la que se calcularon las métricas. Hoy tiene 44 documentos y 44 relaciones.

- KB-001 a KB-036: tres procedimientos por categoría, cada uno en versión guía y FAQ.
- KB-037 a KB-040: política general.
- KB-041: error 401 por reloj desfasado. Es el procedimiento causal y el grafo llega a él por `sintoma:401 → causa:reloj_desfasado`.
- KB-042: rotación de tokens. Es un distractor: habla de tokens pero no resuelve un 401.
- KB-043 y KB-044: exportación por correo (retirado) y descarga directa (vigente). `KB-044 reemplaza_a KB-043`.

## Cómo se carga

```powershell
.\.venv\Scripts\python.exe bootstrap.py      # una vez: crea la base y las tablas
.\.venv\Scripts\python.exe cargar_kb.py      # pide la contrasena; se puede repetir
```

La primera carga informa `{'nuevos': 44, ...}` y las siguientes `{'nuevos': 0, ..., 'sin cambios': 44, ...}`. Antes de tocar la base, `cargar_kb.py` valida el archivo: IDs únicos, campos completos y relaciones que apuntan a documentos que existen.

## Contrato de `retrieve`

```python
retrieve(query: str, category: str, tool: str) -> list[dict]   # tool: lexical | grafo | hibrido
```

Devuelve hasta 3 documentos ordenados por relevancia. Cada uno trae `id`, `categoria`, `titulo`, `version` y `texto`, más el puntaje de la herramienta que lo encontró:

| Herramienta | Qué hace | Puntaje |
|---|---|---|
| `lexical` | TF-IDF con coseno sobre título y texto. Si ninguna palabra coincide, devuelve lista vacía | `score` (0 a 1) |
| `grafo` | Los documentos que `categoria:<category>` documenta, en orden de ID | `score` = 0.0 |
| `hibrido` | Fusión RRF de las dos anteriores | `fusion_score` |

Ejemplo (`lexical`, consulta "error 401 token"):

```json
{"id": "KB-013", "categoria": "api", "titulo": "Error 401 token - Guia operador", "version": 1,
 "texto": "Revisar vencimiento del token y entorno configurado. ...", "score": 0.646523}
```

Si la herramienta no está entre las tres, `ValueError` antes de tocar la base.

## La contraseña

`retrieve` lee PostgreSQL en cada llamada, pero la firma del contrato no le pasa la contraseña. Por eso `run.py`, después de pedirla, la deja en la variable de entorno `PGPASSWORD` de su propio proceso, y psycopg la lee sola desde ahí. Se escribe una sola vez y no queda guardada en ningún archivo.

Si la API se arranca de otra forma (por ejemplo, `uvicorn` directo), hay que definir `PGPASSWORD` en esa terminal. Si falta, `retrieve` lanza `ConnectionError`: `POST /tickets/{id}/analizar` responde 503 y no guarda ninguna ejecución.

## Grafo por síntoma

`mi_grafo.py` recorre hasta dos saltos desde un síntoma, muestra la ruta y no devuelve versiones reemplazadas. Una ruta causal pesa menos (gana) que una ruta por categoría.

```powershell
.\.venv\Scripts\python.exe mi_grafo.py "Codigo 401 al autenticar"
#   KB-041  (2 saltos)  <-  sintoma:401 --posible_causa--> causa:reloj_desfasado --procedimiento--> KB-041
```

Todavía no es una herramienta de `retrieve`: la herramienta `grafo` del contrato es la de categoría.

## Pruebas

`test_marco.py` corre junto con las de Cristian y no necesita PostgreSQL ni Ollama, porque lee `kb.json`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
```

Cubre el gate, las tres herramientas, el grafo, la validez de `kb.json`, el contrato con `analysis.py` y un análisis completo con la KB real y un doble del modelo. Con la misma lista `STOP`, la versión para PostgreSQL de `retrieval.py` devuelve exactamente los mismos documentos y puntajes que la del laboratorio (572 combinaciones de consulta, categoría y herramienta comparadas).
