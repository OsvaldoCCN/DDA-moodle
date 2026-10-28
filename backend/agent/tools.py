import logging
import mysql.connector
from langchain_core.tools import tool

from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
)

logger = logging.getLogger(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

@tool
def consultar_rendimiento_cuestionarios(estudiante_id: int) -> str:
    """
    Usa esta herramienta para consultar las notas y los intentos de un estudiante en sus cuestionarios.
    Útil cuando el estudiante pregunta por sus calificaciones o necesitas evaluar su fase de 'Desempeño' o 'Reflexión' SRL.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute('''
            SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados 
            FROM historico_cuestionarios 
            WHERE estudiante_id = %s
            ORDER BY fecha_registro DESC
        ''', (estudiante_id,))
        
        resultados = cursor.fetchall()
        cursor.close()
        
        if not resultados:
            return "El estudiante aún no ha rendido ningún cuestionario en la base de datos."
            
        respuesta = f"Historial de Cuestionarios del estudiante ID {estudiante_id}:\n"
        for fila in resultados:
            nota_str = f"{fila[3]:.1f}" if fila[3] is not None else "Sin nota"
            minutos_str = f"{fila[4]:.1f}" if fila[4] is not None else "N/A"
            respuesta += f"- Quiz ID {fila[0]} | Intento {fila[1]} | Estado: {fila[2]} | Nota: {nota_str} | Tiempo: {minutos_str} min\n"
            
        return respuesta
    except Exception as e:
        logger.error(f"Error al consultar cuestionarios para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el rendimiento de cuestionarios debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()

@tool
def consultar_esfuerzo_scorm(estudiante_id: int) -> str:
    """
    Usa esta herramienta para revisar si el estudiante ha estudiado el material de clases (paquetes SCORM).
    Útil para la fase de 'Monitoreo' SRL, para saber si el alumno leyó la materia antes de hacer preguntas o evaluaciones.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute('''
            WITH UltimosSCORM AS (
                SELECT moodle_scormid, estado, puntaje, fecha_registro,
                       ROW_NUMBER() OVER(PARTITION BY moodle_scormid ORDER BY fecha_registro DESC) as fila
                FROM historico_scorm 
                WHERE estudiante_id = %s
            )
            SELECT moodle_scormid, estado, puntaje, fecha_registro 
            FROM UltimosSCORM 
            WHERE fila = 1
        ''', (estudiante_id,))
        
        resultados = cursor.fetchall()
        cursor.close()
        
        if not resultados:
            return "El estudiante no registra interacciones en paquetes de contenido (SCORM) aún."
            
        respuesta = f"Progreso de estudio del material (SCORM) para estudiante ID {estudiante_id}:\n"
        for fila in resultados:
            puntaje_texto = f"{fila[2]}%" if fila[2] is not None else "Sin calificar"
            respuesta += f"- Módulo SCORM {fila[0]} | Estado: {fila[1]} | Avance/Puntaje: {puntaje_texto}\n"
            
        return respuesta
    except Exception as e:
        logger.error(f"Error al consultar SCORM para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el progreso de SCORM debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()

tools = [consultar_rendimiento_cuestionarios, consultar_esfuerzo_scorm]
