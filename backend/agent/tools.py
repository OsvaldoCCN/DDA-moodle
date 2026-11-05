import logging
import mysql.connector
import json
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
        
        # OJO: Si historico_cuestionarios tampoco tiene fecha_registro, fallará. 
        # Cambiamos el ORDER BY a numero_intento por seguridad.
        cursor.execute('''
            SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados 
            FROM historico_cuestionarios 
            WHERE estudiante_id = %s
            ORDER BY moodle_quizid, numero_intento DESC
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
    Usa esta herramienta para revisar si el estudiante ha estudiado el material interactivo (SCORM), 
    cuántos intentos realizó y en qué preguntas específicas se equivocó leyendo el suspend_data JSON.
    Útil para la fase de 'Monitoreo' o 'Reflexión' SRL.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Adaptado a la nueva estructura: Sin fecha_registro, usando numero_intento para el orden
        # y extrayendo el suspend_data.
        cursor.execute('''
            SELECT moodle_scormid, numero_intento, estado, puntaje, suspend_data, tiempo_invertido_segundos
            FROM historico_scorm 
            WHERE estudiante_id = %s
            ORDER BY moodle_scormid, numero_intento ASC
        ''', (estudiante_id,))
        
        resultados = cursor.fetchall()
        cursor.close()
        
        if not resultados:
            return "El estudiante no registra interacciones en paquetes de contenido (SCORM) aún."
            
        respuesta = f"Progreso detallado del material interactivo (SCORM) para estudiante ID {estudiante_id}:\n"
        
        for fila in resultados:
            scorm_id = fila[0]
            intento = fila[1]
            estado = fila[2]
            puntaje = f"{fila[3]}%" if fila[3] is not None else "Sin calificar"
            json_respuestas = fila[4]
            tiempo = fila[5]
            
            respuesta += f"\n- Módulo SCORM {scorm_id} (Intento {intento}) | Estado: {estado} | Tiempo: {tiempo}s | Puntaje: {puntaje}\n"
            
            # Formateamos el JSON para que el LLM lo entienda fácil
            if json_respuestas:
                try:
                    datos_json = json.loads(json_respuestas)
                    # Si el JSON tiene la estructura típica de H5P/SCORM con 'answers' o 'reveals'
                    if 'answers' in datos_json:
                        respuesta += "  Respuestas específicas del alumno en este intento:\n"
                        for pregunta_id, datos_respuesta in datos_json['answers'].items():
                            correcta = "Correcta (ok:true)" if datos_respuesta.get('ok') else "Incorrecta (ok:false)"
                            respuesta += f"    * Pregunta {pregunta_id}: {correcta}\n"
                    else:
                        respuesta += f"  Datos internos guardados: {json_respuestas}\n"
                except json.JSONDecodeError:
                    respuesta += f"  Datos internos guardados: {json_respuestas}\n"
            else:
                respuesta += "  No hay registro de respuestas específicas guardadas.\n"
                
        return respuesta
    except Exception as e:
        logger.error(f"Error al consultar SCORM para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el progreso de SCORM debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()

tools = [consultar_rendimiento_cuestionarios, consultar_esfuerzo_scorm]