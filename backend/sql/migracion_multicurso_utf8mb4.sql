USE srl_tesis_db;

-- 1. Asegurar codificación utf8mb4 en la base de datos y tablas existentes
ALTER DATABASE srl_tesis_db
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

ALTER TABLE cursos CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE actividades_curso CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE estudiantes CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE curso_estudiantes CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE historico_scorm CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE historico_cuestionarios CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE interacciones_bot CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE resumen_lad_estudiante CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. interacciones_bot: agregar moodle_courseid (DEFAULT 3 para conservar registros del curso piloto) e índice compuesto
ALTER TABLE interacciones_bot
  ADD COLUMN moodle_courseid INT NOT NULL DEFAULT 3 AFTER estudiante_id,
  ADD INDEX idx_interacciones_est_curso (estudiante_id, moodle_courseid);

-- 3. historico_cuestionarios: agregar moodle_courseid (DEFAULT 3 para conservar registros del curso piloto)
ALTER TABLE historico_cuestionarios
  ADD COLUMN moodle_courseid INT NOT NULL DEFAULT 3 AFTER estudiante_id,
  ADD INDEX idx_cuestionarios_est_curso (estudiante_id, moodle_courseid);

-- 4. resumen_lad_estudiante: agregar metas de planeación por curso
ALTER TABLE resumen_lad_estudiante
  ADD COLUMN meta_nota_porcentaje DECIMAL(5,2) DEFAULT 70.00,
  ADD COLUMN meta_minutos_semanales INT DEFAULT 60;

