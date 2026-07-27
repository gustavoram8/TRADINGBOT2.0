-- ¿Queda algún contador de IDs atrasado en PostgreSQL?
--
-- Un contador atrasado hace que la próxima inserción choque contra una fila
-- existente ("duplicate key ... already exists"). El servidor lo repara solo al
-- arrancar; esto es para comprobarlo con los ojos, sin modificar nada.
--
--   psql "$DATABASE_URL" -f tools/check_pg_sequences.sql
--
-- Cero filas = todo en orden. Cualquier fila = esa tabla fallaría al insertar.
SELECT t.tablename                       AS tabla,
       COALESCE(s.last_value, 0)         AS contador,
       (xpath('/row/max/text()',
              query_to_xml(format('SELECT COALESCE(MAX(%I),0) AS max FROM %I.%I',
                                  a.attname, t.schemaname, t.tablename),
                           false, true, '')))[1]::text::bigint AS id_mas_alto
FROM pg_tables t
JOIN pg_class c     ON c.relname = t.tablename
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.schemaname
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
JOIN pg_sequences s ON (s.schemaname || '.' || s.sequencename)
     = pg_get_serial_sequence(quote_ident(t.schemaname) || '.' || quote_ident(t.tablename), a.attname)
WHERE t.schemaname = 'public'
  AND (xpath('/row/max/text()', query_to_xml(
        format('SELECT COALESCE(MAX(%I),0) AS max FROM %I.%I', a.attname, t.schemaname, t.tablename),
        false, true, '')))[1]::text::bigint > COALESCE(s.last_value, 0)
ORDER BY 1;
