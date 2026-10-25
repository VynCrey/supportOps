# Base de conocimiento: contenido y procedencia de las relaciones

KB versión del 25/10/2026: **56 documentos y 92 relaciones** (`kb.json`). Las tablas de resultados tienen que indicar con qué versión de la KB se midieron: con los 12 documentos nuevos, las métricas medidas con 44 documentos dejan de valer.

## Documentos

| IDs | Qué son | Origen |
|---|---|---|
| KB-001 a KB-036 | 3 procedimientos por categoría, cada uno en versión guía y FAQ con el mismo texto | kit (`seed.py`) |
| KB-037 a KB-040 | Política general | kit (`seed.py`) |
| KB-041 | Error 401 por reloj desfasado: procedimiento causal | manual, P4 |
| KB-042 | Rotación programada de tokens: distractor (habla de tokens y no resuelve un 401) | manual, P4 |
| KB-043 / KB-044 | Exportación por correo (retirado) / descarga directa (vigente) | manual, P4 |
| KB-045 a KB-056 | 2 procedimientos nuevos por categoría, cada uno con su ruta síntoma → causa → procedimiento. Están escritos para competir con uno que ya existe (por ejemplo, KB-045 "Bloqueo por intentos fallidos" contra KB-002 "Cuenta bloqueada") | Marco, P4 |

Los 12 nuevos siguen las reglas del kit: dicen qué verificar, qué datos pedir y qué no prometer. Ninguno pide credenciales, afirma acciones ya realizadas ni promete plazos.

## Relaciones que no son "categoría documenta documento"

Una relación `posible_causa` **no demuestra causalidad**: dice que, ante ese síntoma, vale la pena revisar esa causa primero. Las propuso quien escribió el procedimiento y las revisó Marco.

| Origen | Relación | Destino | Sale de | Propuso | Revisó | Fecha |
|---|---|---|---|---|---|---|
| `sintoma:401` | pertenece_a | `categoria:api` | KB-041 | manual de ejecución (P4) | Marco | 22/10/2026 |
| `sintoma:401` | posible_causa | `causa:reloj_desfasado` | KB-041 | manual de ejecución (P4) | Marco | 22/10/2026 |
| `causa:reloj_desfasado` | procedimiento | `KB-041` | KB-041 | manual de ejecución (P4) | Marco | 22/10/2026 |
| `KB-044` | reemplaza_a | `KB-043` | KB-044 | manual de ejecución (P4) | Marco | 22/10/2026 |
| `sintoma:intentos_fallidos` | pertenece_a | `categoria:acceso` | KB-045 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:intentos_fallidos` | posible_causa | `causa:bloqueo_temporal` | KB-045 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:bloqueo_temporal` | procedimiento | `KB-045` | KB-045 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:segundo_factor` | pertenece_a | `categoria:acceso` | KB-046 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:segundo_factor` | posible_causa | `causa:dispositivo_desactualizado` | KB-046 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:dispositivo_desactualizado` | procedimiento | `KB-046` | KB-046 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:pago_rechazado` | pertenece_a | `categoria:facturacion` | KB-047 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:pago_rechazado` | posible_causa | `causa:medio_de_pago_vencido` | KB-047 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:medio_de_pago_vencido` | procedimiento | `KB-047` | KB-047 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:cobro_distinto` | pertenece_a | `categoria:facturacion` | KB-048 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:cobro_distinto` | posible_causa | `causa:cambio_de_plan` | KB-048 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:cambio_de_plan` | procedimiento | `KB-048` | KB-048 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:500` | pertenece_a | `categoria:api` | KB-049 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:500` | posible_causa | `causa:incidente_del_servicio` | KB-049 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:incidente_del_servicio` | procedimiento | `KB-049` | KB-049 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:webhook` | pertenece_a | `categoria:api` | KB-050 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:webhook` | posible_causa | `causa:url_sin_respuesta` | KB-050 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:url_sin_respuesta` | procedimiento | `KB-050` | KB-050 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:caracteres_raros` | pertenece_a | `categoria:exportacion` | KB-051 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:caracteres_raros` | posible_causa | `causa:codificacion_distinta` | KB-051 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:codificacion_distinta` | procedimiento | `KB-051` | KB-051 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:exportacion_incompleta` | pertenece_a | `categoria:exportacion` | KB-052 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:exportacion_incompleta` | posible_causa | `causa:limite_de_filas` | KB-052 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:limite_de_filas` | procedimiento | `KB-052` | KB-052 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:sms` | pertenece_a | `categoria:notificaciones` | KB-053 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:sms` | posible_causa | `causa:numero_mal_registrado` | KB-053 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:numero_mal_registrado` | procedimiento | `KB-053` | KB-053 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:correo_corporativo` | pertenece_a | `categoria:notificaciones` | KB-054 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:correo_corporativo` | posible_causa | `causa:filtro_del_servidor` | KB-054 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:filtro_del_servidor` | procedimiento | `KB-054` | KB-054 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:cambio_de_email` | pertenece_a | `categoria:seguridad` | KB-055 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:cambio_de_email` | posible_causa | `causa:toma_de_cuenta` | KB-055 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:toma_de_cuenta` | procedimiento | `KB-055` | KB-055 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:clave_expuesta` | pertenece_a | `categoria:seguridad` | KB-056 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `sintoma:clave_expuesta` | posible_causa | `causa:credencial_filtrada` | KB-056 | Marco, borrador con Claude | Marco | 25/10/2026 |
| `causa:credencial_filtrada` | procedimiento | `KB-056` | KB-056 | Marco, borrador con Claude | Marco | 25/10/2026 |

## Cómo arranca el grafo por síntoma

`mi_grafo.py` arranca en un síntoma cuando la consulta trae **todas** sus palabras clave: `sintoma:pago_rechazado` necesita "pago" y "rechazado" (se acepta plural o sufijo). Los códigos de tres cifras (`sintoma:401`, `sintoma:500`) arrancan solos.

Hasta el 25/10 alcanzaba con que una palabra de la consulta fuera parte del nombre del síntoma. Con 13 síntomas eso hacía que "la" arrancara en `sintoma:clave_expuesta`. El límite conocido de la regla nueva es que no entiende sinónimos ni conjugaciones: "Me rechazaron el pago" no arranca. Está escrito como prueba en `test_marco.py`.
