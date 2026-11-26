import mysql.connector
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

# Corrección en el formato del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT"),
        charset="utf8mb4",
        use_unicode=True
    )

def sincronizar_actividades_cron(course_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    
    logger.info(f"--- [CRON] Ejecutando sincronización periódica del Curso ID: {course_id} ---")

    # 1. Obtener Quizzes y SCORMs activos
    raw_quizzes = call_moodle_api("mod_quiz_get_quizzes_by_courses", courseids=[course_id])
    if not raw_quizzes:
        logger.warning("CRON: No se pudieron obtener quizzes o no existen en el curso.")
        quizzes = []
    else:
        quizzes = MoodleSRLParser.limpiar_quizzes(raw_quizzes)
    
    raw_scorms = call_moodle_api("mod_scorm_get_scorms_by_courses", courseids=[course_id])
    scorms = MoodleSRLParser.limpiar_scorms(raw_scorms) if raw_scorms else []

    # 1.5 Guardar o actualizar catálogo de actividades (nombres y fechas de cierre)
    for quiz in quizzes:
        cursor.execute('''
            INSERT INTO actividades_curso (moodle_courseid, tipo, instancia_id, nombre, fecha_cierre)
            VALUES (%s, 'quiz', %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre),
                fecha_cierre = VALUES(fecha_cierre)
        ''', (
            course_id,
            quiz['quiz_id'],
            quiz['nombre'],
            quiz.get('fecha_cierre') or 0
        ))

    for scorm in scorms:
        cursor.execute('''
            INSERT INTO actividades_curso (moodle_courseid, tipo, instancia_id, nombre)
            VALUES (%s, 'scorm', %s, %s)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre)
        ''', (
            course_id,
            scorm['scorm_id'],
            scorm['nombre']
        ))

    # 2. Obtener los estudiantes registrados localmente en este curso
    cursor.execute('''
        SELECT e.id, e.moodle_userid, e.anon_id 
        FROM estudiantes e
        INNER JOIN curso_estudiantes ce ON e.id = ce.estudiante_id
        INNER JOIN cursos c ON ce.curso_id = c.id
        WHERE c.moodle_courseid = %s
    ''', (course_id,))
    estudiantes = cursor.fetchall()

    # Si aún no hay curso_estudiantes cargados para este curso, hacemos fallback a todos los estudiantes
    if not estudiantes:
        cursor.execute("SELECT id, moodle_userid, anon_id FROM estudiantes")
        estudiantes = cursor.fetchall()

    if not estudiantes:
        logger.warning("CRON: No hay estudiantes registrados en la BD local. Ejecuta el sincronizador manual primero.")
        cursor.close()
        conexion.close()
        return

    # 3. Sincronizar solo notas/intentos de los estudiantes existentes
    for est in estudiantes:
        estudiante_local_id = est['id']
        moodle_userid = est['moodle_userid']
        
        # Sync Quizzes
        for quiz in quizzes:
            quiz_id = quiz['quiz_id']
            raw_attempts = call_moodle_api("mod_quiz_get_user_attempts", quizid=quiz_id, userid=moodle_userid)
            if raw_attempts:
                intentos = MoodleSRLParser.limpiar_intentos_cuestionario(
                    raw_attempts,
               quiz['puntaje_maximo']          
                )
                for intento in intentos:
                    ts_quiz = intento.get("fecha_fin") or intento.get("fecha_inicio")
                    fecha_quiz = datetime.fromtimestamp(ts_quiz) if ts_quiz and ts_quiz > 0 else None

                    cursor.execute('''
                        INSERT INTO historico_cuestionarios
                        (estudiante_id, moodle_courseid, moodle_quizid, numero_intento, estado, nota, nota_maxima, minutos_usados, fecha_registro)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
                        ON DUPLICATE KEY UPDATE
                            estado = VALUES(estado),
                            nota = VALUES(nota),
                            nota_maxima = VALUES(nota_maxima),
                            minutos_usados = VALUES(minutos_usados),
                            fecha_registro = COALESCE(%s, fecha_registro)
                    ''', (
                        estudiante_local_id,
                        course_id,
                        quiz_id,
                        intento["numero_intento"],
                        intento["estado"],
                        intento["nota"],
                        intento["nota_maxima"],
                        intento["minutos_usados"],
                        fecha_quiz,
                        fecha_quiz
                    ))


        # Sync SCORMs (Lógica de Producción Multi-Intento)
        for scorm in scorms:
            scorm_id = scorm['scorm_id']
            res_scoes = call_moodle_api("mod_scorm_get_scorm_scoes", scormid=scorm_id)
            
            if not res_scoes or "scoes" not in res_scoes:
                continue

            intento = 1
            while True:
                estado_final = "incomplete"
                tiempo_total = 0
                puntaje_final = 0.0
                suspend_data_final = None
                fecha_scorm_ts = 0
                hubo_interaccion = False
                tracks_encontrados_en_intento = False
                
                for sco in res_scoes["scoes"]:
                    scoid = sco.get('id')
                    
                    raw_tracks = call_moodle_api(
                        "mod_scorm_get_scorm_sco_tracks", 
                        userid=moodle_userid, 
                        scoid=scoid,
                        attempt=intento
                    )
                    
                    if raw_tracks and "data" in raw_tracks and "tracks" in raw_tracks["data"]:
                        if len(raw_tracks["data"]["tracks"]) > 0:
                            tracks_encontrados_en_intento = True
                            
                        datos_sco = MoodleSRLParser.limpiar_tracking_scorm(raw_tracks)
                        
                        if datos_sco["estado"] not in ["incomplete", "desconocido"] or datos_sco["suspend_data"] or datos_sco["tiempo_segundos"] > 0:
                            hubo_interaccion = True
                            
                        if datos_sco["estado"] in ["completed", "passed"]:
                            estado_final = "completed"
                            
                        tiempo_total += datos_sco["tiempo_segundos"]
                        puntaje_final = max(puntaje_final, datos_sco["puntaje_raw"])
                        
                        if datos_sco["suspend_data"]:
                            suspend_data_final = datos_sco["suspend_data"]

                        if datos_sco.get("fecha_actividad"):
                            fecha_scorm_ts = max(fecha_scorm_ts, datos_sco["fecha_actividad"])
                
                if not tracks_encontrados_en_intento:
                    break
                
                if hubo_interaccion:
                    fecha_scorm = datetime.fromtimestamp(fecha_scorm_ts) if fecha_scorm_ts > 0 else None
                    cursor.execute('''
                        INSERT INTO historico_scorm 
                        (estudiante_id, moodle_courseid, moodle_scormid, numero_intento, estado, tiempo_invertido_segundos, puntaje, suspend_data, fecha_registro)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
                        ON DUPLICATE KEY UPDATE 
                            estado = VALUES(estado),
                            tiempo_invertido_segundos = VALUES(tiempo_invertido_segundos),
                            puntaje = VALUES(puntaje),
                            suspend_data = VALUES(suspend_data),
                            fecha_registro = COALESCE(%s, fecha_registro)
                    ''', (estudiante_local_id, course_id, scorm_id, intento, estado_final, tiempo_total, puntaje_final, suspend_data_final, fecha_scorm, fecha_scorm))
                    logger.info(f"  + SCORM ID {scorm_id}: Intento {intento} guardado para {est['anon_id']}.")
                
                intento += 1

    conexion.commit()
    cursor.close()
    conexion.close()
    logger.info("--- [CRON] Sincronización de actividades finalizada ---")


if __name__ == "__main__":
    CURSOS_ACTIVOS = [5]
    for cid in CURSOS_ACTIVOS:
        sincronizar_actividades_cron(cid)