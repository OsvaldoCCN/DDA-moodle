import mysql.connector
import os
import logging
from dotenv import load_dotenv

load_dotenv(override=True)


from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

# Configurar logging para el CRON
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def sincronizar_curso(course_id: int):
    """
    Función principal para el CRON.
    Descubre actividades y estudiantes en un curso y sincroniza sus datos.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    logger.info(f"--- Iniciando sincronización del Curso ID: {course_id} ---")

    # 1. Descubrir Quizzes y SCORMs en el curso
    logger.info("Descubriendo actividades del curso...")
    raw_quizzes = call_moodle_api("mod_quiz_get_quizzes_by_courses", courseids=[course_id])
    quizzes = MoodleSRLParser.limpiar_quizzes(raw_quizzes)
    
    raw_scorms = call_moodle_api("mod_scorm_get_scorms_by_courses", courseids=[course_id])
    scorms = MoodleSRLParser.limpiar_scorms(raw_scorms)

    # 2. Descubrir Estudiantes matriculados
    logger.info("Obteniendo estudiantes matriculados...")
    raw_users = call_moodle_api("core_enrol_get_enrolled_users", courseid=course_id)
    
    # Filtramos solo los que tienen rol de estudiante (suponiendo que Moodle devuelve todos)
    estudiantes_moodle = [user for user in raw_users if user.get('id')] 

    # 3. Iterar y Sincronizar
    for estudiante in estudiantes_moodle:
        moodle_userid = estudiante.get('id')
        nombre_estudiante = estudiante.get('fullname')
        
        logger.info(f"Sincronizando estudiante: {nombre_estudiante} (Moodle ID: {moodle_userid})")
        
        # Asegurar estudiante en BD local
        cursor.execute("INSERT IGNORE INTO estudiantes (moodle_userid, nombre) VALUES (%s, %s)", 
                       (moodle_userid, nombre_estudiante))
        conexion.commit()
        
        cursor.execute("SELECT id FROM estudiantes WHERE moodle_userid = %s", (moodle_userid,))
        estudiante_local_id = cursor.fetchone()[0]

        # Sincronizar Quizzes
        for quiz in quizzes:
            quiz_id = quiz['quiz_id']
            sincronizar_intentos_quiz(cursor, moodle_userid, estudiante_local_id, quiz_id)

        # Sincronizar SCORMs
        for scorm in scorms:
            scorm_id = scorm['scorm_id']
            # Para SCORM necesitamos el SCOID. Obtenemos la lista de SCOs de este SCORM:
            raw_scos = call_moodle_api("mod_scorm_get_scorm_scos", scormid=scorm_id)
            scos = raw_scos.get('scos', [])
            
            for sco in scos:
                # Filtrar scos que no tienen tracking (como carpetas o estructuras visuales vacías)
                if sco.get('scormtype') == 'sco':
                    scoid = sco.get('id')
                    sincronizar_tracking_scorm(cursor, moodle_userid, estudiante_local_id, course_id, scorm_id, scoid)

    conexion.commit()
    cursor.close()
    conexion.close()
    logger.info("--- Sincronización completada ---")


def sincronizar_intentos_quiz(cursor, moodle_userid, estudiante_local_id, quiz_id):
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
            logger.info(f"  + Quiz {quiz_id}: Nuevo intento {intento['numero_intento']} guardado.")

def sincronizar_tracking_scorm(cursor, moodle_userid, estudiante_local_id, course_id, scorm_id, scoid):
    raw_tracks = call_moodle_api("mod_scorm_get_scorm_sco_tracks", userid=moodle_userid, scoid=scoid)
    datos_scorm = MoodleSRLParser.limpiar_tracking_scorm(raw_tracks)
    
    if datos_scorm.get("estado") != "desconocido":
        cursor.execute('''
            INSERT INTO historico_scorm 
            (estudiante_id, moodle_courseid, moodle_scormid, estado, tiempo_invertido_segundos, puntaje)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (estudiante_local_id, course_id, scorm_id, 
              datos_scorm.get("estado"), datos_scorm.get("tiempo_segundos"), datos_scorm.get("puntaje_raw")))
        logger.info(f"  + SCORM {scorm_id}: Tracking guardado (Estado: {datos_scorm.get('estado')}).")

if __name__ == "__main__":
    CURSO_PILOTO_ID = 5
    sincronizar_curso(CURSO_PILOTO_ID)