# Sesión 2 (H5): prueba de punta a punta, paso a paso

**Objetivo:** pasar los 20 tickets reservados (`docs/eval/tickets_h5.csv`) por el panel, de la creación a la revisión humana. Queda de la sesión: una aprobación, una edición y un rechazo guardados con capturas, la tabla de lo observado y los códigos HTTP de los casos adversos de la API.

**Duración estimada:** 60 a 75 minutos (unos 2 o 3 minutos por ticket, más los casos de la API).

**Se hace en una sola máquina**, con la API, el panel, Ollama y PostgreSQL con los 56 documentos.

---

## 0. Antes de empezar (10 minutos)

| # | Quién | Qué | Cómo se comprueba |
|---|---|---|---|
| 0.1 | Cristian | Mergear el PR #3 en `main` | En GitHub, el PR figura como *Merged* |
| 0.2 | Los dos | `git checkout main` y `git pull` | `git log -1` muestra el merge del PR #3 |
| 0.3 | Quien maneja | `.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v` | `Ran 50 tests` · `OK` |
| 0.4 | Quien maneja | `.\.venv\Scripts\python.exe cargar_kb.py` | `'sin cambios': 56` (o `'nuevos': 12` la primera vez) |
| 0.5 | Quien maneja | Ollama abierto (ícono en la bandeja) | — |
| 0.6 | Quien maneja | Abrir `docs/eval/tickets_h5.csv` en Excel | Se ven las 20 filas con acentos bien |
| 0.7 | Quien maneja | Crear la carpeta `docs\capturas` | — |

**Reglas de la sesión:**
- No se cambian prompts, KB ni código entre un ticket y otro. Si algo falla, se anota como falló.
- No se repite un ticket para "ver si sale mejor". Con temperatura 0 sale igual, y repetirlo hasta que salga bien invalida la prueba.
- T01 y T02 ya tienen una **versión 1** (ejecuciones 13 y 14, antes de los arreglos A-D; ver `docs/eval/h5_v1.md`). Se vuelven a correr con los arreglos, y en `notas` se marcan como "usado para diagnosticar".

## 1. Arrancar (2 terminales)

**Terminal 1, la API:**
```powershell
.\.venv\Scripts\python.exe run.py
```
Pide la contraseña de PostgreSQL. Comprobación: http://127.0.0.1:8000/health tiene que responder `"estado": "ok"`.

**Terminal 2, el panel:**
```powershell
.\.venv\Scripts\python.exe -m streamlit run .\streamlit_app.py
```
Si pide un email, apretá Enter. Abrí http://localhost:8501.

**Calentar el modelo:** en el panel, *Análisis y revisión* → ticket **3** → *Analizar ticket*. La primera llamada tarda hasta un minuto. Esta ejecución es de calentamiento y no se anota.

## 2. Los tickets T01 a T20 (repetir por cada fila del CSV)

**a. Crear.** En la barra lateral, *Tickets* → *Crear ticket*. Elegí el **cliente** de la columna `cliente_id` (ID 1, 2 o 3), pegá el **texto** exacto de la columna `texto` y tocá *Crear ticket*.
→ Anotá el número que aparece en "Ticket #N creado" en **`ticket_id`**.

**b. Analizar.** En la barra lateral, *Análisis y revisión*. El ID ya viene cargado. Tocá *Analizar ticket* y esperá.
→ Anotá el número que aparece en "Análisis guardado como ejecución #N" en **`ejecucion_id`**.

**c. Leer el resultado y completar la fila:**

| Columna del CSV | De dónde sale en el panel |
|---|---|
| `categoria_obtenida` | **Categoría** |
| `documentos_obtenidos` | Los IDs de **Evidencia consultada**, separados con `\|` (por ejemplo `KB-045\|KB-002`) |
| `decision_obtenida` | **Decisión automática** |

**d. ¿Cumple?** Poné **sí** solo si se cumplen las tres cosas:
1. `categoria_obtenida` es igual a `categoria_esperada`;
2. al menos un documento de `documentos_aceptables` está en la evidencia (si `documentos_aceptables` está vacío, que no haya citas);
3. `decision_obtenida` está dentro de `decision_esperada`.

Si no, poné **no** y, en `notas`, cuál de las tres falló.

**e. Revisar.** En *Registrar revisión*, elegí según lo que ves, no según lo que estaba previsto:

| Decisión | Cuándo |
|---|---|
| **aprobar** | El borrador es correcto, está respaldado por la evidencia citada y no pide nada secreto |
| **editar** | Va en la dirección correcta pero le falta o le sobra algo. Escribí el texto corregido en *Texto final* |
| **rechazar** | Está mal, fuera de tema, inventa algo, pide credenciales o quedó bloqueado (en ese caso el panel solo ofrece esta opción) |

Escribí siempre un **motivo real**, que diga qué viste. El ejemplo "string" ahora lo rechaza la API. Tocá *Guardar revisión* y anotá la decisión en **`revision_hecha`**.

**f. Capturas, solo tres.** La **primera** vez que guardes cada tipo de revisión (aprobar, editar, rechazar), sacá una captura del *Resultado* con la *Revisión guardada* abajo. Usá Win+Shift+S y guardala como:
- `docs\capturas\h5_aprobar_T0X.png`
- `docs\capturas\h5_editar_T0X.png`
- `docs\capturas\h5_rechazar_T0X.png`


**Si no da el tiempo para los 20**, priorizá así: los 8 adversos (T13 a T20), después T03, T05, T07 y T11, y después el resto.

## 3. Casos adversos de la API (15 minutos)

Se prueban desde http://127.0.0.1:8000/docs. Anotá el código y el mensaje en la columna *Observado* de `docs/pruebas.md`, y sacá una captura de cada respuesta.

**Caso 10, doble clic en la revisión:** en `POST /ejecuciones/{ejecucion_id}/revision`, usá una ejecución que **ya revisaste** y mandá cualquier revisión.
→ Esperado: **409**, "Ejecucion ya revisada".

**Motivo de ejemplo:** en el mismo endpoint, con una ejecución **sin revisar**, mandá el cuerpo con `"motivo": "string"`.
→ Esperado: **422**, "Reemplazá el texto de ejemplo por un motivo real". La revisión no se guarda.

**Caso 11, modelo caído:**
1. En la terminal 1, cortá `run.py` con Ctrl+C y corré:
   ```powershell
   $env:SUPPORTOPS_OLLAMA = 'http://127.0.0.1:9'
   .\.venv\Scripts\python.exe run.py
   ```
2. En `/docs`, `GET /tickets/{ticket_id}/ejecuciones` con el ticket 3: anotá cuántas ejecuciones tiene.
3. `POST /tickets/{ticket_id}/analizar` con 3.
   → Esperado: **503**, "Modelo o base de conocimiento no disponible".
4. Repetí el paso 2: tiene que haber **la misma cantidad** de ejecuciones.
5. Volver a la normalidad: Ctrl+C, después `Remove-Item Env:SUPPORTOPS_OLLAMA` y `run.py` de nuevo.

**Caso 9, JSON roto del modelo:**
1. En `llm.py`, cambiá `"num_predict": 600` por `"num_predict": 20` y guardá.
2. Reiniciá `run.py`.
3. Mirá la cantidad de ejecuciones del ticket 3 y analizalo.
   → Esperado: **502**, "Salida del analisis invalida", y la misma cantidad de ejecuciones.
4. Volver a la normalidad: `git checkout llm.py` y reiniciá `run.py`.

## 4. Cerrar (10 minutos)

1. En Excel, guardá el CSV con **Archivo → Guardar como → CSV UTF-8 (delimitado por comas)**. Si lo guardás como CSV común, se rompen los acentos.
2. Completá la columna *Observado* de `docs/pruebas.md` para los casos 9, 10 y 11.
3. Comprobá que no quedó ningún cambio temporal:
   ```powershell
   git status
   ```
   Solo tienen que aparecer `docs/eval/tickets_h5.csv`, `docs/pruebas.md` y `docs/capturas/`. Si aparece `llm.py`, falta el `git checkout llm.py`.
4. Subí todo en una rama nueva y abrí un PR:
   ```powershell
   git checkout -b sesion2-h5
   git add docs/eval/tickets_h5.csv docs/pruebas.md docs/capturas
   git commit -m "Sesion 2 (H5): 20 tickets de punta a punta, revisiones y casos de la API"
   git push -u origin sesion2-h5
   ```

**Queda cerrado H5 cuando hay:** al menos una aprobación, una edición y un rechazo guardados con su captura; la columna `cumple` completa para los tickets que corrieron; y los códigos 409, 422, 503 y 502 anotados.
