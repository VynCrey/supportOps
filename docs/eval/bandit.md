# P10: bandit con cinco semillas, leído con honestidad

## Qué se probó

Un bandit contextual elige la herramienta de búsqueda (`lexical`, `grafo` o `hibrido`) según el estado *categoría + si la consulta trae un código*, y se compara contra la **mejor política fija**.

| | |
|---|---|
| Entrenamiento | 33 casos: el título de cada procedimiento de `kb.json` como consulta |
| Prueba | Las 15 consultas con respuesta de `docs/eval/consultas.csv`, escritas antes de medir y separadas del entrenamiento (lo verifica una prueba automática) |
| Algoritmo | ε-greedy (ε = 0,2), 500 episodios, media incremental de la recompensa |
| Recompensa | 1 si el documento correcto está en el top-3, menos el costo de la herramienta |
| Costo | Proporcional a la **latencia medida**, con tope 0,05 para que solo desempate y nunca pese más que un acierto. La medición se guarda en `docs/eval/latencias.json` y se reutiliza (`python bandit.py --medir` la repite) |
| Semillas | 1, 7, 13, 42, 99 |
| Corrida guardada | `docs/eval/bandit_semillas.json` |

## Resultado

| Política | Hit@3 | MRR@3 |
|---|---|---|
| `lexical` fija | 0,47 | 0,38 |
| `grafo` fija | **0,53** | 0,38 |
| `hibrido` fija | **0,53** | 0,42 |
| Bandit, si `lexical` sale más barata | 0,47 ± 0,00 (**−0,07**) | 0,38 |
| Bandit, si `hibrido` sale más barata | 0,53 ± 0,00 (**±0,00**) | 0,42 |

**En ningún caso el bandit supera a la mejor política fija.** Según qué herramienta salga más barata en la medición, empata con ella o queda 0,07 abajo. La corrida guardada es una de las dos, y en `bandit_semillas.json` está cuál.

## Por qué

**1. En el entrenamiento, `lexical` e `hibrido` aciertan siempre.** Las consultas de entrenamiento son títulos de documentos y comparten palabras con la respuesta. Las dos herramientas llegan a un valor aprendido de ≈ 0,95 en todos los estados, y el bandit no tiene ningún caso que las diferencie.

**2. Entonces decide el costo, y el costo entre esas dos es ruido.** `hibrido` hace lo mismo que `lexical` más el grafo, que tarda unos 0,01 ms. La diferencia real es menor al 1 %, y el ruido de la medición es mucho mayor. En mediciones repetidas en la misma máquina, `hibrido` salió entre un 11 % más rápida y un 11 % más lenta que `lexical`. El script avisa cuando la diferencia queda por debajo del 5 %. El grafo sí se distingue: es unas 100 veces más rápido.

**3. La prueba castiga lo que el entrenamiento no ve.** En palabras de cliente, `lexical` es la peor herramienta (0 de 5 sinónimos). Si el desempate cae del lado de `lexical`, el bandit lo paga en la prueba; si cae del lado de `hibrido`, empata con la mejor fija. Ninguna de las dos situaciones la decidió el aprendizaje.

**4. Desvío cero no quiere decir estabilidad: quiere decir que no había nada que decidir.** Las cinco semillas eligen la misma herramienta en las 15 consultas.

**5. La mejor política fija también tiene un límite.** `grafo` gana en parte porque en la evaluación recibe la categoría correcta (ver `metricas.md`). En el sistema real depende del triage.

## Qué lo haría útil

En orden de impacto, y sin tocar las 20 consultas de prueba:

1. **Entrenar con consultas en palabras de cliente**, con sinónimos y casos ambiguos, escritas aparte de las de prueba. Es lo único que le da al bandit casos donde `lexical` e `hibrido` rindan distinto.
2. **Que la herramienta `grafo` use las rutas por síntoma.** Hoy devuelve la categoría ordenada por ID, y eso le quita al bandit una opción que de verdad sea distinta.
3. **Agregar al estado algo que separe los casos**, por ejemplo si la consulta comparte palabras con algún título.

## Cómo reportarlo

> "El bandit no supera a la mejor política fija: según la medición de latencia, empata (±0,00 de Hit@3) o queda 0,07 abajo, con desvío 0 en 5 semillas. En el entrenamiento, con títulos de documentos, `lexical` e `hibrido` aciertan siempre; la elección entre ellas la decide una diferencia de costo que está dentro del ruido de la medición. El techo lo pone la distribución de las consultas de entrenamiento, no el algoritmo."
