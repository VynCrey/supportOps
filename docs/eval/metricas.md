# P7: métricas de recuperación y análisis de fallos

## Condiciones

| | |
|---|---|
| Fecha | 25/10/2026 |
| KB | 56 documentos, 92 relaciones (`kb.json`, huella `cdbfeba5`) |
| Consultas | 20, escritas antes de medir (commit `2bbfd46`): 10 normales, 5 sinónimos, 5 sin respuesta |
| k | 3 |
| Cómo se corrió | `python evaluar.py`, sobre `kb.json`, con las mismas funciones de ranking que `retrieve()` |
| Detalle por consulta | `docs/eval/resultados.csv` |

## Resultados

| Herramienta | Hit@3 | MRR@3 | Hit@3 normales (10) | Hit@3 sinónimos (5) | Abstención correcta (5) |
|---|---|---|---|---|---|
| `lexical` | 0,47 (7/15) | 0,38 | 0,70 | **0,00** | 40 % (2/5) |
| `grafo` | 0,53 (8/15) | 0,38 | **0,40** | 0,80 | 100 % (5/5)\* |
| `hibrido` | 0,53 (8/15) | 0,42 | 0,50 | 0,60 | 40 % (2/5) |

\* En la evaluación el grafo recibe la **categoría esperada**, no la que decide el triage. Su resultado es un techo, y su abstención perfecta sale de que a las consultas sin respuesta se les asignó `general`, que no tiene documentos en el grafo. En el sistema real, ambos dependen de que el triage acierte.

## Cómo se lee

- **`lexical` acierta cuando el cliente usa las palabras del documento, y solo entonces.** En las normales llega a 0,70, y en 5 de sus 7 aciertos el documento correcto sale primero. En los sinónimos no acierta ninguno: tres veces devuelve lista vacía y dos veces un documento equivocado.
- **`grafo` no mira la consulta.** Devuelve los tres primeros documentos de la categoría por ID. Por eso le va bien en los sinónimos (las respuestas son documentos viejos, de ID bajo) y mal en las normales (seis respuestas son documentos nuevos, de ID alto).
- **`hibrido` tiene el mejor MRR (0,42), pero hereda las dos debilidades:** las ofertas equivocadas del léxico en las consultas sin respuesta y el orden por ID del grafo.

## Análisis de fallos

**1. Una sola palabra en común decide, aunque no tenga que ver con el problema.** TF-IDF le da más peso a las palabras raras, sin mirar el significado:

| Consulta | Devolvió primero | Palabra en común |
|---|---|---|
| E09 "Me llegan **dos** mails iguales por cada aviso" | KB-008 Cobro duplicado | "dos" ("los dos cobros") |
| E14 "No me aceptaron el débito **automático**" | KB-002 Cuenta bloqueada | "automático" ("desbloqueo automático") |
| E18 "Quiero un descuento por pagar el año **completo**" | KB-053 SMS no recibido | "completo" ("número completo") |
| E20 "¿Cómo exporto los **datos** directo a Google Sheets?" | KB-007 Factura | "datos" ("sin datos bancarios") |
| E08 "**Antes** me mandaban la exportación por mail…" | KB-019 Archivo CSV | "antes" ("antes de exportar") |

**2. Sinónimos: el léxico no los cubre (0 de 5).** "Perdí mi contraseña" (E11), "el link caducó" (E12) y "no recibo notificaciones en mi casilla" (E15) devuelven lista vacía. "Me frena la API" (E13) y "no me aceptaron el débito" (E14) devuelven documentos equivocados. Es el argumento medido para evaluar embeddings en P11.

**3. Los competidores de P4 funcionan como se diseñaron.** En E02 ("me bloquearon la cuenta después de equivocarme varias veces") gana KB-002, Cuenta bloqueada genérica, sobre KB-045, Bloqueo por intentos fallidos. La consulta solo comparte con los dos la palabra "cuenta", y el documento genérico es más corto. Elegir mal es posible, que era el objetivo de P4.

**4. La herramienta `grafo` no usa las rutas por síntoma de P5.** `retrieve(..., "grafo")` devuelve la categoría ordenada por ID. Los 12 procedimientos nuevos (KB-045 a KB-056) y la versión vigente KB-044 tienen ID más alto que los seis documentos base de su categoría, así que **nunca entran en el top-3**: por eso fallan E02, E05, E06, E07, E08 y E10. Las rutas síntoma → causa → procedimiento existen en `mi_grafo.py`, pero `retrieve()` todavía no las consulta.

**5. Abstención: el léxico siempre ofrece algo.** En tres de las cinco consultas sin respuesta propone procedimientos: E16 (factura en dólares → documentos de factura), E18 y E20. Solo se abstiene cuando no hay ninguna palabra en común (E17 "integrar con SAP", E19 "app para el celular"). `hibrido` hereda los mismos tres errores.

## Conclusiones para el informe

1. Ninguna herramienta sirve sola: `lexical` falla en los sinónimos y en la abstención, y `grafo` falla en todo lo que no sea "el primer documento de la categoría".
2. El problema principal de `lexical` no es el orden sino la cobertura: cuando acierta, casi siempre acierta primero.
3. La mejora de P5 no llega al sistema mientras `retrieve()` no use las rutas por síntoma. Es el siguiente cambio a medir con estas mismas 20 consultas.

## Límites

- Son 15 consultas con respuesta: **una consulta mueve el Hit@3 en 0,07**. Los resultados indican tendencias; no son tasas estables.
- El grafo se evalúa con la categoría correcta, lo que lo favorece.
- Una sola versión de la KB y un solo valor de k.
- Las consultas no se tocan más. Si el sistema cambia, se vuelve a medir con estas mismas 20 y se compara.
