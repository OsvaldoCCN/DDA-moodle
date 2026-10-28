import mysql.connector
from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

import os
from dotenv import load_dotenv


load_dotenv() 

def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def sincronizar_estudiante(moodle_userid, nombre_estudiante, course_id, quiz_id, scorm_id, scoid):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Asegurar que el estudiante exista (Sintaxis MySQL: INSERT IGNORE)
    cursor.execute("INSERT IGNORE INTO estudiantes (moodle_userid, nombre) VALUES (%s, %s)", 
                   (moodle_userid, nombre_estudiante))
    
    cursor.execute("SELECT id FROM estudiantes WHERE moodle_userid = %s", (moodle_userid,))
    estudiante_local_id = cursor.fetchone()[0]

    print(f"Sincronizando datos para {nombre_estudiante} (ID Moodle: {moodle_userid}, ID Local: {estudiante_local_id})...")

    print(" -> Extrayendo y guardando Cuestionarios...")
    raw_attempts = call_moodle_api("mod_quiz_get_user_attempts", quizid=quiz_id, userid=moodle_userid)
    intentos = MoodleSRLParser.limpiar_intentos_cuestionario(raw_attempts)
    
    for intento in intentos:
        cursor.execute('''
            SELECT id FROM historico_cuestionarios 
            WHERE estudiante_id = %s AND moodle_quizid = %s AND numero_intento = %s
        ''', (estudiante_local_id, quiz_id, intento["numero_intento"]))
        
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO historico_cuestionarios 
                (estudiante_id, moodle_quizid, numero_intento, estado, nota, minutos_usados)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (estudiante_local_id, quiz_id, intento["numero_intento"], 
                  intento["estado"], intento["nota"], intento["minutos_usados"]))
            print(f"    + Nuevo intento {intento['numero_intento']} guardado (Nota: {intento['nota']})")
        else:
            print(f"    - Intento {intento['numero_intento']} ya estaba registrado.")

    print(" -> Extrayendo y guardando SCORM...")
    raw_tracks = call_moodle_api("mod_scorm_get_scorm_sco_tracks", userid=moodle_userid, scoid=scoid)
    datos_scorm = MoodleSRLParser.limpiar_tracking_scorm(raw_tracks)
    
    if datos_scorm.get("estado") != "desconocido":
        cursor.execute('''
            INSERT INTO historico_scorm 
            (estudiante_id, moodle_courseid, moodle_scormid, estado, tiempo_invertido_segundos, puntaje)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (estudiante_local_id, course_id, scorm_id, 
              datos_scorm.get("estado"), datos_scorm.get("tiempo_segundos"), datos_scorm.get("puntaje_raw")))
        print(f"    + Snapshot de SCORM guardado (Estado: {datos_scorm.get('estado')}, Puntaje: {datos_scorm.get('puntaje_raw')})")

    conexion.commit()
    conexion.close()
    print(" Sincronización completada con éxito.\n")

if __name__ == "__main__":
    # Disparador manual para Debug / Cron local
    ID_ALUMNO = 3
    NOMBRE = "Osvaldo Casas"
    ID_CURSO = 2
    ID_CUESTIONARIO = 1
    ID_SCORM = 1
    ID_SCO = 2
    
    sincronizar_estudiante(ID_ALUMNO, NOMBRE, ID_CURSO, ID_CUESTIONARIO, ID_SCORM, ID_SCO)