-- Ejecutar en supportops_final. Todas estas consultas son de solo lectura.

SELECT (SELECT COUNT(*) FROM clientes) AS clientes,
       (SELECT COUNT(*) FROM tickets) AS tickets,
       (SELECT COUNT(*) FROM eventos) AS eventos,
       (SELECT COUNT(*) FROM documentos) AS documentos;

SELECT categoria_real, COUNT(*) AS cantidad
FROM tickets
GROUP BY categoria_real
ORDER BY cantidad DESC, categoria_real;

SELECT estado, COUNT(*) AS cantidad
FROM tickets
GROUP BY estado
ORDER BY estado;

SELECT c.plan, COUNT(*) AS cantidad
FROM tickets AS t
JOIN clientes AS c ON c.id = t.cliente_id
GROUP BY c.plan
ORDER BY c.plan;

SELECT COUNT(*) AS tickets,
       COUNT(DISTINCT texto) AS textos_distintos,
       COUNT(DISTINCT familia) AS familias,
       COUNT(*) FILTER (
           WHERE primera_respuesta < creado OR resuelto < creado
              OR (resuelto IS NOT NULL AND estado <> 'resuelto')
       ) AS fechas_o_estado_incoherentes
FROM tickets;

SELECT percentile_cont(0.5) WITHIN GROUP (
           ORDER BY (EXTRACT(EPOCH FROM (primera_respuesta - creado)) / 60.0)::float8
       ) AS mediana_primera_respuesta_min,
       percentile_cont(0.9) WITHIN GROUP (
           ORDER BY (EXTRACT(EPOCH FROM (primera_respuesta - creado)) / 60.0)::float8
       ) AS p90_primera_respuesta_min,
       percentile_cont(0.5) WITHIN GROUP (
           ORDER BY (EXTRACT(EPOCH FROM (resuelto - creado)) / 60.0)::float8
       ) AS mediana_resolucion_min,
       percentile_cont(0.9) WITHIN GROUP (
           ORDER BY (EXTRACT(EPOCH FROM (resuelto - creado)) / 60.0)::float8
       ) AS p90_resolucion_min
FROM tickets;

SELECT decision, COUNT(*) AS cantidad
FROM revisiones
GROUP BY decision
ORDER BY decision;
