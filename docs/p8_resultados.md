# P8 — Roles contra el modelo real

Fecha: 14/10/2026 · Modelo: `qwen2.5:3b` en Ollama · `temperature: 0` (misma entrada, misma salida: verificado repitiendo una corrida).

Corridas hechas en el laboratorio de Marco (kit con SQLite), antes de integrar con este repo.

## 1. Conocimiento (`probar_rol.py`, triage fijo en `api`)

Único cambio entre las dos columnas: se agregó al prompt *"En motivo explica en una frase por que elegiste esa herramienta."*

| Ticket | Antes: herramienta · motivo · docs · seg | Después: herramienta · docs · seg |
|---|---|---|
| La API devuelve 401 al integrar pedidos | hibrido · "hora del error" · KB-013, 014, 016 · 3.7 | **lexical** · KB-013, 016, 041 · 1.3 |
| Tengo un problema con la facturacion | hibrido · "facturacion" · KB-007, 013, 008 · 3.6 | hibrido · KB-007, 013, 008 · 1.2 |
| No me llegan los avisos por mail | lexical · "api" · KB-026, 029, 025 · 0.6 | **hibrido** · KB-013, 026, 014 · 1.3 |

- Antes, el motivo era una palabra copiada de la entrada (`faltantes`, ticket, categoría). El modelo leía "motivo" como *motivo de la consulta*. Con la frase, explica la elección.
- Una sola frase cambió 2 de 3 decisiones. El 401 ahora sigue la regla del prompt (`lexical`); "avisos" pasó a `hibrido` y recupera peor.
- El motivo se genera **después** de la herramienta (orden del esquema): justifica una elección ya hecha.
- Los detalles inventados en los motivos (API, interfaz, backend, horarios) y KB-013/014 en tickets ajenos a la API vienen del triage fijo del script, no del rol.

## 2. Supervisor

| Fuente | Orden del esquema | Borrador | Esperado | Respondió | Motivos | Seg |
|---|---|---|---|---|---|---|
| probar_rol | decision primero | sin respaldo ("el token se renueva cada 24 h") | revisar | **listo ✗** | explicación correcta, contradice la decisión | 2.8 |
| probar_rol | motivos primero | sin respaldo | revisar | revisar ✓ | solo IDs | 0.8 |
| probar_rol | motivos primero | con respaldo (repite KB-013) | listo | listo ✓ | resumen de la evidencia | 1.8 |
| flujo, ejec. 1 | motivos primero | copia del ticket, citas mal formadas | revisar | **listo ✗** | resumen de la evidencia | 3.4 |
| flujo, ejec. 2 | motivos primero | aplica KB-026 (avisos duplicados) a avisos que no llegan; citas mal formadas | revisar | **listo ✗** | repite el borrador y agrega un consejo nuevo | 4.5 |

- Poner `motivos` antes de `decision` hizo que el supervisor distinga en el par controlado. En el flujo real, con borradores desprolijos, dijo `listo` las dos veces: **2 de 5 juicios correctos**.
- Los motivos nunca evalúan el borrador: resumen la evidencia o lo reescriben. El supervisor actúa como un segundo redactor.

## 3. Flujo completo (`flujo.py`, cuatro roles reales)

| Rol | Ejec. 1 — "La API devuelve error 401 con el token…" | Ejec. 2 — "No me llegan los avisos por mail" |
|---|---|---|
| Triage | `seguridad` ✗ (esperado `api`) | `seguridad` ✗ (esperado `notificaciones`) |
| Conocimiento | `lexical` ✓ · KB-013, 016, 041 | `lexical` ✓ · KB-026, 029, 025 |
| Borrador | repite el ticket; citas con el texto del documento en vez del ID | texto razonable; citas con el JSON entero del documento |
| Supervisor (modelo) | listo | listo |
| Gate | **bloquear** — cita inexistente en evidencia | **bloquear** — cita inexistente en evidencia |
| Segundos | triage 1.7 · conoc. 1.1 · borrador 4.6 · superv. 3.4 · **total 11.0** | 1.0 · 1.7 · 6.1 · 4.5 · **total 13.4** |

- El gate atajó los dos borradores que el supervisor del modelo aprobó. Es la razón de tener una regla determinista además del rol LLM.
- En la ejecución 1 el gate frenó por el **formato** de las citas, no por el contenido. Con las citas bien escritas, un borrador que solo repite el ticket habría salido `listo` (queda documentado en `test_limite_borrador_que_copia_el_ticket`).
- La recuperación salió bien a pesar del triage equivocado porque `lexical` no usa la categoría. Con `grafo` o `hibrido` habría traído documentos de seguridad.

## 4. Cambios llevados a este repo

Las mediciones se hicieron en el laboratorio de Marco, con el `agents.py` del kit. En este repo los dos cambios están en `analysis.py`:

1. Prompt de conocimiento: se agrega *"En motivo explica en una frase por que elegiste esa herramienta."*
2. Clase `Supervision`: `motivos` se declara antes que `decision`, así el esquema JSON que recibe el modelo trae los motivos primero.

Los prompts de `analysis.py` no son idénticos a los del kit, así que el efecto hay que volver a medirlo acá con el modelo real.

## 5. Para Cristian (triage y borrador)

- **Triage:** en el laboratorio dio `seguridad` en 2 de 2 tickets. El prompt de este repo ya agrega la regla "401/403/429 → api", que puede resolverlo: hay que medirlo con tickets que no sean de API (en el laboratorio también falló "No me llegan los avisos por mail").
- **Borrador:** `citas` acepta cualquier texto. Pasar los IDs de la evidencia como `enum` de los ítems obligaría al modelo a devolver solo IDs reales. Mientras no se resuelva, si el borrador vuelve a escribir texto en `citas`, el gate bloquea todo y la revisión solo admite rechazo: no se pueden registrar la aprobación ni la edición que pide H5.

## 6. Límites de estas mediciones

- Son 3 tickets de conocimiento y 5 juicios del supervisor: indican tendencias, no miden tasas.
- El triage fijo de `probar_rol.py` contamina los resultados de conocimiento que dependen de la categoría.
- Tiempos medidos en una sola máquina; varían entre 0.6 y 6.1 s por llamada y 11–13 s por ticket.

## 7. Primera corrida integrada (repo de Cristian, 23/10/2026)

Ticket 3 de la muestra de `bootstrap.py` ("La API devuelve error 401 con el token"), analizado desde `/docs` con `qwen2.5:3b`, la KB cargada en PostgreSQL y los prompts de `analysis.py`. Ejecución 1.

| Rol | Salida | Seg | Lectura |
|---|---|---|---|
| Triage | `api` · faltantes vacíos | 59.0 | ✓ correcto (en el laboratorio había dado `seguridad`). El tiempo es la carga del modelo en la primera llamada |
| Conocimiento | `hibrido` · motivo: "Necesito saber si el error es frecuente y si hay un token expirado o incorrecto" | 1.4 | El motivo es una oración pero explica el problema, no la herramienta. Con un código exacto se esperaba `lexical` |
| Recuperación | KB-013, KB-014, KB-016 | — | Viene de PostgreSQL (`base_conocimiento: conectada`). KB-014 (error 403) entra por la parte de grafo; KB-041 (reloj desfasado), que `lexical` trae tercero, queda afuera |
| Borrador | texto = el ticket repetido · citas `KB-013`, `KB-016` · los pasos del procedimiento puestos en `preguntas` | 2.5 | Citas correctas (el problema del laboratorio no apareció). El texto no propone nada |
| Supervisor (modelo) | motivos primero, decisión `revisar` | 2.6 | El orden nuevo del esquema se respetó. Los motivos repiten las preguntas |
| Gate | **`bloquear`** · "Solicitud de credenciales detectada" | — | Falso positivo, ver abajo |

**Por qué se bloqueó.** `pide_credenciales` (`safety.py`) bloquea toda pregunta o faltante que contenga una palabra como "token", aunque no pida su valor. Lo disparó "Revisar vencimiento del token y entorno configurado". Reproducido aparte: la misma frase en `texto` no bloquea, porque ahí la regla exige un verbo de pedido seguido de un secreto; "Enviame tu token" en `preguntas` sí bloquea, como corresponde.

**Consecuencia para H5.** En los tickets de error 401 casi cualquier pregunta menciona el token, y un borrador bloqueado solo admite rechazo. Hasta que se ajuste la regla o el borrador deje de poner pasos en `preguntas`, esos tickets no permiten registrar una aprobación ni una edición.

**Detalle cosmético.** En `hibrido`, KB-013 muestra `score: 0` porque la fusión conserva la copia del documento que llega por el grafo. El orden lo decide `fusion_score`. Pasa igual en el laboratorio.
