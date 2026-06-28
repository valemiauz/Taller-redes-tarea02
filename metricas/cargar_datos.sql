-- cargar_datos.sql
-- Crea una tabla 'carga' con ~50.000 filas (~7 MB) para que la consulta
-- de medicion (SELECT/COPY) transfiera un volumen util y se pueda medir el
-- throughput del enlace bajo distintas condiciones de red (delay / loss).

DROP TABLE IF EXISTS carga;

CREATE TABLE carga AS
SELECT
    g                       AS id,
    md5(g::text)            AS hash1,
    md5((g * 7)::text)      AS hash2,
    repeat('x', 80)         AS relleno
FROM generate_series(1, 50000) AS g;

-- Tabla pequeña usada en las demostraciones de modificacion (Tarea 2/3)
DROP TABLE IF EXISTS tareas;
CREATE TABLE tareas (id SERIAL PRIMARY KEY, nombre_ramo VARCHAR(50));
INSERT INTO tareas (nombre_ramo) VALUES ('Taller de Redes');

SELECT count(*) AS filas_carga FROM carga;
