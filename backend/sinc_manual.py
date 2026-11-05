import mysql.connector
import os
import logging
import uuid
from dotenv import load_dotenv

load_dotenv()

from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

# Corrección en el formato del logging para evitar saltos de línea accidentales
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def registrar_y_sincronizar_curso(course_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    logger.info(f"--- [MANUAL] Iniciando registro y sincronización del Curso ID: {course_id} ---")

    # 1. Obtener Quizzes y SCORMs
    logger.info("Descubriendo actividades del curso...")
    raw_quizzes = call_moodle_api("mod_quiz_get_quizzes_by_courses", courseids=[course_id])
    
    if not raw_quizzes:
        logger.error("Sincronización abortada: No se pudieron obtener los quizzes.")
        cursor.close()
        conexion.close()
        return
        
    quizzes = MoodleSRLParser.limpiar_quizzes(raw_quizzes)
    
    raw_scorms = call_moodle_api("mod_scorm_get_scorms_by_courses", courseids=[course_id])
    scorms = MoodleSRLParser.limpiar_scorms(raw_scorms) if raw_scorms else []

    # 2. Descubrir y Registrar Estudiantes
    logger.info("Obteniendo estudiantes matriculados en Moodle...")
    raw_users = call_moodle_api("core_enrol_get_enrolled_users", courseid=course_id)
    
    if not raw_users:
        logger.error("Sincronización abortada: No se pudo obtener la lista de usuarios.")
        cursor.close()
        conexion.close()
        return

    estudiantes_moodle = [user for user in raw_users if user.get('id')] 

    for estudiante in estudiantes_moodle:
        moodle_userid = estudiante.get('id')
        email = estudiante.get('email', f"sin_correo_{moodle_userid}@local")
        
        anon_id = f"usr-{uuid.uuid4().hex[:8]}" 
        
        logger.info(f"Registrando/Verificando estudiante ID Moodle: {moodle_userid} (Anon: {anon_id})")
        
        cursor.execute('''
            INSERT IGNORE INTO estudiantes (moodle_userid, email, anon_id) 
            VALUES (%s, %s, %s)
        ''', (moodle_userid, email, anon_id))
        conexion.commit()
        
        cursor.execute("SELECT id FROM estudiantes WHERE moodle_userid = %s", (moodle_userid,))
        resultado = cursor.fetchone()
        
        if not resultado:
            logger.error(f"Error al obtener el ID local para el estudiante {moodle_userid}")
            continue
            
        estudiante_local_id = resultado[0]

        # Sincronizar Quizzes
        for quiz in quizzes:
            sincronizar_intentos_quiz(cursor, moodle_userid, estudiante_local_id, quiz['quiz_id'])

        # Sincronizar SCORMs delegando la extracción de SCOs a la función de tracking
        for scorm in scorms:
            sincronizar_tracking_scorm(cursor, moodle_userid, estudiante_local_id, course_id, scorm['scorm_id'])

    conexion.commit()
    cursor.close()
    conexion.close()
    logger.info("--- [MANUAL] Registro y sincronización completados ---")


def sincronizar_intentos_quiz(cursor, moodle_userid, estudiante_local_id, quiz_id):
    raw_attempts = call_moodle_api("mod_quiz_get_user_attempts", quizid=quiz_id, userid=moodle_userid)
    if not raw_attempts:
        return
        
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


def sincronizar_tracking_scorm(cursor, moodle_userid, estudiante_local_id, course_id, scorm_id):
    """
    Sincroniza un SCORM guardando todos sus intentos (Intento 1, 2, 3...) vía API oficial.
    """
    res_scoes = call_moodle_api("mod_scorm_get_scorm_scoes", scormid=scorm_id)
    if not res_scoes or "scoes" not in res_scoes:
        return

    intento = 1
    while True:
        estado_final = "incomplete"
        tiempo_total = 0
        puntaje_final = 0.0
        suspend_data_final = None
        hubo_interaccion = False
        tracks_encontrados_en_intento = False

        for sco in res_scoes["scoes"]:
            scoid = sco.get("id")
            
            # Consultamos dinámicamente el intento actual (1, 2, 3...)
            tracks = call_moodle_api(
                "mod_scorm_get_scorm_sco_tracks", 
                userid=moodle_userid, 
                scoid=scoid, 
                attempt=intento
            )
            
            # Verificamos si Moodle devolvió datos para este intento
            if tracks and "data" in tracks and "tracks" in tracks["data"]:
                if len(tracks["data"]["tracks"]) > 0:
                    tracks_encontrados_en_intento = True
                    
                datos_sco = MoodleSRLParser.limpiar_tracking_scorm(tracks)
                
                if datos_sco["estado"] not in ["incomplete", "desconocido"] or datos_sco["suspend_data"] or datos_sco["tiempo_segundos"] > 0:
                    hubo_interaccion = True
                    
                if datos_sco["estado"] in ["completed", "passed"]:
                    estado_final = "completed"
                    
                tiempo_total += datos_sco["tiempo_segundos"]
                puntaje_final = max(puntaje_final, datos_sco["puntaje_raw"])
                
                if datos_sco["suspend_data"]:
                    suspend_data_final = datos_sco["suspend_data"]

        # Si iteramos todos los SCOs y ninguno tenía tracks para el intento N, 
        # significa que el alumno no tiene más intentos. Salimos del bucle while.
        if not tracks_encontrados_en_intento:
            break

        # Si hubo interacción, guardamos este intento específico en MySQL
        if hubo_interaccion:
            cursor.execute('''
                INSERT INTO historico_scorm 
                (estudiante_id, moodle_courseid, moodle_scormid, numero_intento, estado, tiempo_invertido_segundos, puntaje, suspend_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    estado = VALUES(estado),
                    tiempo_invertido_segundos = VALUES(tiempo_invertido_segundos),
                    puntaje = VALUES(puntaje),
                    suspend_data = VALUES(suspend_data)
            ''', (estudiante_local_id, course_id, scorm_id, intento, estado_final, tiempo_total, puntaje_final, suspend_data_final))
            
            logger.info(f"  + SCORM ID {scorm_id}: Intento {intento} guardado (Estado: {estado_final}).")
        
        # Pasamos a consultar el siguiente intento
        intento += 1


if __name__ == "__main__":
    CURSO_PILOTO_ID = 3
    registrar_y_sincronizar_curso(CURSO_PILOTO_ID)