# Integracion con Marco

## Punto de partida

Cristian preparo las siete tablas en `schema.sql`, una muestra ficticia con
`bootstrap.py` y la API en `main.py`. `POST /tickets/{id}/analizar` ya llama
cuatro roles con Ollama, guarda el resultado y permite revision humana. Mientras
no haya documentos ni recuperador, la evidencia es vacia y la supervision exige
revision. Nunca se considera una respuesta respaldada por documentos.

La muestra local es pequena: 3 clientes, 6 tickets y 18 eventos. La base
`supportops_final` y la contrasena de PostgreSQL son locales; no se suben a Git.
Cada colaborador crea su propia base ejecutando `bootstrap.py` tras instalar
`requirements.txt`. Ver instrucciones completas en el README.

## Contrato de recuperacion

`knowledge_adapter.py` intenta importar `retrieve` de un archivo `retrieval.py`
en la raiz del repositorio. La funcion debe aceptar tres cadenas:

```python
def retrieve(query: str, category: str, tool: str) -> list[dict]:
    ...
```

`tool` recibe `lexical`, `grafo` o `hibrido`. Debe devolver una lista de
documentos, ordenada por relevancia. Cada documento necesita al menos un `id`
de tipo texto; se recomienda incluir `titulo`, `categoria`, `version` y `texto`
para que el borrador pueda usar y citar la evidencia. El analisis usa hasta los
tres primeros documentos. Los IDs citados deben coincidir exactamente con los
IDs devueltos; una cita inexistente bloquea el borrador.

Las tablas `documentos` y `relaciones` estan disponibles. `documentos` usa
`id TEXT`, `categoria TEXT`, `titulo TEXT`, `version INTEGER` y `texto TEXT`.
`relaciones` usa `origen TEXT`, `relacion TEXT` y `destino TEXT`.
Coordinemos antes de cambiar estas columnas o el formato de `retrieve`.

## Como verificar la integracion

1. Ejecutar las pruebas: `python -m unittest discover -s . -p 'test_*.py' -v`.
2. Cargar documentos ficticios en PostgreSQL y arrancar API y Ollama.
3. Analizar un ticket en `/docs`; comprobar `evidencia`, `borrador.citas`,
   `supervision` y `base_conocimiento` en la respuesta.
4. Usar el `ejecucion_id` de esa respuesta para consultar la ejecucion y
   registrar una revision humana.

No usar datos de clientes reales ni subir claves o contrasenas al repositorio.
