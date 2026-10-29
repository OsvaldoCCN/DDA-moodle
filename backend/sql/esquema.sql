-- 1. Crear la base de datos si no existe y seleccionarla
CREATE DATABASE IF NOT EXISTS srl_tesis_db;
USE srl_tesis_db;

-- 2. Tabla principal de Estudiantes
CREATE TABLE IF NOT EXISTS estudiantes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    moodle_userid INT UNIQUE,
    nombre VARCHAR(255) NOT NULL
);

-- 3. Tabla para guardar el progreso diario de los SCORM (Esfuerzo y Monitoreo)
CREATE TABLE IF NOT EXISTS historico_scorm (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT,
    moodle_courseid INT,
    moodle_scormid INT,
    estado VARCHAR(50),
    tiempo_invertido_segundos INT,
    puntaje FLOAT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);

-- 4. Tabla para guardar los intentos de Cuestionarios (Reflexión y Desempeño)
CREATE TABLE IF NOT EXISTS historico_cuestionarios (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT,
    moodle_quizid INT,
    numero_intento INT,
    estado VARCHAR(50),
    nota FLOAT,
    minutos_usados FLOAT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);

-- 5. Tabla para el historial del Agente Socrático
CREATE TABLE IF NOT EXISTS interacciones_bot (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT,
    mensaje_usuario TEXT,
    respuesta_agente TEXT,
    contexto_srl_inyectado TEXT,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);
