-- Tabla principal de Estudiantes
CREATE TABLE estudiantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    moodle_userid INTEGER UNIQUE,
    nombre TEXT NOT NULL
);

-- Tabla para guardar el progreso diario de los SCORM (Esfuerzo y Monitoreo)
CREATE TABLE historico_scorm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER,
    moodle_courseid INTEGER,
    moodle_scormid INTEGER,
    estado TEXT, -- 'completed', 'incomplete', 'passed'
    tiempo_invertido_segundos INTEGER,
    puntaje REAL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);

-- Tabla para guardar los intentos de Cuestionarios (Reflexión y Desempeño)
CREATE TABLE historico_cuestionarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER,
    moodle_quizid INTEGER,
    numero_intento INTEGER,
    estado TEXT, -- 'finished', 'inprogress'
    nota REAL,
    minutos_usados REAL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);

-- Tabla para el historial del Agente Socrático (Para analizar tu tesis después)
CREATE TABLE interacciones_bot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER,
    mensaje_usuario TEXT,
    respuesta_agente TEXT,
    contexto_srl_inyectado TEXT, -- Qué datos tenía LangGraph al momento de responder
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
);