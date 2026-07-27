-- ¿Queda algún contador de IDs que vaya a chocar en la próxima inserción?
--
-- Un contador guarda DOS cosas: su último valor y si alguna vez fue leído
-- (is_called). Mientras no lo hayan leído entrega ese mismo valor, así que una
-- tabla con una sola fila en id=1 y el contador parado en 1 sin leer también
-- choca. Por eso se compara contra el id que el contador entregaría de verdad.
--
--   psql "$DATABASE_URL" -f tools/check_pg_sequences.sql
--
-- Cero filas = todo en orden. Cualquier fila = esa tabla fallaría al insertar.
WITH t AS (
  SELECT c.relname AS tabla,
         a.attname AS col,
         pg_get_serial_sequence(quote_ident(n.nspname) || '.' || quote_ident(c.relname),
                                a.attname) AS seq
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
  JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
  WHERE c.relkind = 'r'
), d AS (
  SELECT t.tabla, t.seq,
         (xpath('/row/max/text()', query_to_xml(
            format('SELECT COALESCE(MAX(%I),0) AS max FROM public.%I', t.col, t.tabla),
            false, true, '')))[1]::text::bigint AS id_mas_alto,
         (xpath('/row/lv/text()', query_to_xml(
            format('SELECT last_value AS lv FROM %s', t.seq), false, true, '')))[1]::text::bigint AS contador,
         (xpath('/row/ic/text()', query_to_xml(
            format('SELECT is_called AS ic FROM %s', t.seq), false, true, '')))[1]::text::boolean AS fue_leido
  FROM t WHERE t.seq IS NOT NULL
)
SELECT tabla, contador, fue_leido, id_mas_alto,
       CASE WHEN fue_leido THEN contador + 1 ELSE contador END AS proximo_id
FROM d
WHERE id_mas_alto > 0
  AND (CASE WHEN fue_leido THEN contador + 1 ELSE contador END) <= id_mas_alto
ORDER BY 1;
