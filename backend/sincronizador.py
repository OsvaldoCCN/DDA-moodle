import sqlite3
from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

DB_NAME = "srl_tesis.db"

def sincronizar_estudiante(moodle_userid, nombre_estudiante, course_id, quiz_id, scorm_id, scoid):
    # Conectar a la Base de Datos local
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # Asegurar que el estudiante exista en nuestra BD local
    cursor.execute("INSERT OR IGNORE INTO estudiantes (moodle_userid, nombre) VALUES (?, ?)", 
                   (moodle_userid, nombre_estudiante))
    
    # Obtener el ID interno de nuestra base de datos para este estudiante
    cursor.execute("SELECT id FROM estudiantes WHERE moodle_userid = ?", (moodle_userid,))
    estudiante_local_id = cursor.fetchone()[0]

    print(f"Sincronizando datos para {nombre_estudiante} (ID Moodle: {moodle_userid}, ID Local: {estudiante_local_id})...")


    print(" -> Extrayendo y guardando Cuestionarios...")
    raw_attempts = call_moodle_api("mod_quiz_get_user_attempts", quizid=quiz_id, userid=moodle_userid)
    intentos = MoodleSRLParser.limpiar_intentos_cuestionario(raw_attempts)
    
    for intento in intentos:
        cursor.execute('''
            SELECT id FROM historico_cuestionarios 
            WHERE estudiante_id = ? AND moodle_quizid = ? AND numero_intento = ?
        ''', (estudiante_local_id, quiz_id, intento["numero_intento"]))
        
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO historico_cuestionarios 
                (estudiante_id, moodle_quizid, numero_intento, estado, nota, minutos_usados)
                VALUES (?, ?, ?, ?, ?, ?)
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
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (estudiante_local_id, course_id, scorm_id, 
              datos_scorm.get("estado"), datos_scorm.get("tiempo_segundos"), datos_scorm.get("puntaje_raw")))
        print(f"    + Snapshot de SCORM guardado (Estado: {datos_scorm.get('estado')}, Puntaje: {datos_scorm.get('puntaje_raw')})")


    conexion.commit()
    conexion.close()
    print(" Sincronización completada con éxito.\n")

if __name__ == "__main__":
    # datos reales que validamos en nuestras pruebas - debug
    ID_ALUMNO = 3
    NOMBRE = "Osvaldo Casas"
    ID_CURSO = 2
    ID_CUESTIONARIO = 1
    ID_SCORM = 1
    ID_SCO = 2
    
    sincronizar_estudiante(ID_ALUMNO, NOMBRE, ID_CURSO, ID_CUESTIONARIO, ID_SCORM, ID_SCO)