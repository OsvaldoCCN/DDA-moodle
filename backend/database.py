import sqlite3
import os

DB_NAME = "srl_tesis.db"

def inicializar_bd():
    # Conecta a la base de datos (si no existe, crea el archivo)
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # Tabla de Estudiantes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moodle_userid INTEGER UNIQUE,
        nombre TEXT NOT NULL
    )
    ''')

    # Tabla del Histórico de Cuestionarios (Reflexión)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico_cuestionarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        moodle_quizid INTEGER,
        numero_intento INTEGER,
        estado TEXT,
        nota REAL,
        minutos_usados REAL,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
    )
    ''')

    # Tabla del Histórico de SCORM (Monitoreo)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS historico_scorm (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        moodle_courseid INTEGER,
        moodle_scormid INTEGER,
        estado TEXT,
        tiempo_invertido_segundos INTEGER,
        puntaje REAL,
        fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
    )
    ''')

    # Tabla para el Agente (Interacciones y Contexto)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interacciones_bot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        mensaje_usuario TEXT,
        respuesta_agente TEXT,
        contexto_srl_inyectado TEXT,
        fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
    )
    ''')

    conexion.commit()
    conexion.close()
    print(f"Base de datos '{DB_NAME}' inicializada con éxito.")

if __name__ == "__main__":
    inicializar_bd()