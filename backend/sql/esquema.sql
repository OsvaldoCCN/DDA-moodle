-- 1. Crear la base de datos si no existe y seleccionarla
CREATE DATABASE IF NOT EXISTS srl_tesis_db;
USE srl_tesis_db;

-- 2. Tabla principal de Estudiantes (anonimizada)
CREATE TABLE IF NOT EXISTS estudiantes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    moodle_userid INT UNIQUE,
    nombre VARCHAR(255) NULL,
    email VARCHAR(255) UNIQUE NULL,
    anon_id VARCHAR(50) UNIQUE NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla para guardar el progreso de SCORM (Monitoreo y Esfuerzo)
CREATE TABLE IF NOT EXISTS historico_scorm (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    moodle_courseid INT NOT NULL,
    moodle_scormid INT NOT NULL,
    estado VARCHAR(50),
    tiempo_invertido_segundos INT DEFAULT 0,
    puntaje FLOAT DEFAULT 0.0,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_scorm_track (estudiante_id, moodle_courseid, moodle_scormid)
);

-- 4. Tabla para guardar los intentos de Cuestionarios (Reflexión y Desempeño)
CREATE TABLE IF NOT EXISTS historico_cuestionarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    moodle_quizid INT NOT NULL,
    numero_intento INT NOT NULL,
    estado VARCHAR(50),
    nota FLOAT DEFAULT 0.0,
    minutos_usados FLOAT DEFAULT 0.0,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_intento (estudiante_id, moodle_quizid, numero_intento)
);

-- 5. Tabla para el historial del Agente Socrático
CREATE TABLE IF NOT EXISTS interacciones_bot (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    mensaje_usuario TEXT NOT NULL,
    respuesta_agente TEXT NOT NULL,
    contexto_srl_inyectado TEXT,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE
);

-- 6. Nueva Tabla: Resumen de Métricas para el LAD y Contexto del Tutor
CREATE TABLE IF NOT EXISTS resumen_lad_estudiante (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    moodle_courseid INT NOT NULL,
    promedio_quizzes FLOAT DEFAULT 0.0,
    total_quizzes_completados INT DEFAULT 0,
    tiempo_total_scorm_minutos INT DEFAULT 0,
    porcentaje_progreso_curso FLOAT DEFAULT 0.0,
    nivel_riesgo_srl ENUM('bajo', 'medio', 'alto') DEFAULT 'bajo',
    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
    UNIQUE KEY unique_estudiante_curso (estudiante_id, moodle_courseid)
);