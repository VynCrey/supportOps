# Ficha de datos de SupportOps

## Origen y propósito

Todos los clientes, tickets y eventos creados por `bootstrap.py` y
`generar_datos.py` son ficticios. Sirven para comprobar consultas SQL, volumen,
integridad referencial, API y recorrido de la interfaz. No describen el
comportamiento de una empresa ni contienen información de clientes reales.

## Volumen

La muestra inicial contiene 3 clientes, 6 tickets y 18 eventos. Si se ejecuta
`generar_datos.py --aplicar`, el objetivo total es 500 clientes, 20.000 tickets
y 60.000 eventos. Se agregan tres eventos por ticket generado. El generador
no crea documentos ni relaciones de conocimiento; la base documental queda a
cargo de Marco.

## Reglas de generación

- Se usa `random.Random(42)` para elegir categorías, variantes y clientes. La
  selección es reproducible con la misma muestra inicial y versión del código.
- Hay seis categorías, 18 familias y 54 frases base. Cada frase recibe un
  número de caso para identificar la fila; eso aumenta la cantidad de textos
  distintos, pero no la diversidad semántica.
- Seguridad tiene un peso menor (8 %) que las otras categorías. La distribución
  observada exacta debe calcularse en la base, no deducirse de esos pesos.
- Los clientes nuevos tienen planes Basic, Pro y Enterprise en rotación.
- Las fechas generadas empiezan el 2 de septiembre de 2026, en UTC, y se
  separan un minuto por caso. La primera respuesta y la resolución suceden
  después de la creación. La muestra inicial usa el 1 de septiembre de 2026.
- Aproximadamente dos de cada cinco tickets generados quedan resueltos por
  regla. No representa una tasa real de servicio.

## Controles y limitaciones

El esquema comprueba claves foráneas, categorías de plan/estado/prioridad y
orden básico de fechas. El generador se detiene si los eventos existentes no
son tres por ticket y comprueba los conteos finales antes de confirmar la
transacción. Una ejecución adicional sobre la base completa no duplica filas.

Las frases se repiten con cambios superficiales. No son adecuadas para afirmar
calidad de clasificación, recuperación, cumplimiento de SLA ni satisfacción de
clientes reales. Las revisiones humanas no se generan artificialmente. Los
resultados del modelo y las evaluaciones deben medirse en corridas propias.

Para obtener los conteos y hallazgos de la instalación local, ejecutar
`eda.py`. Las consultas SQL están en [consultas_eda.sql](consultas_eda.sql).
