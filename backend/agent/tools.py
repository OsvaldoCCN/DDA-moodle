import mysql.connector
from langchain_core.tools import tool


from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
)


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
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute('''
        SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados 
        FROM historico_cuestionarios 
        WHERE estudiante_id = %s
        ORDER BY fecha_registro DESC
    ''', (estudiante_id,))
    
    resultados = cursor.fetchall()
    conexion.close()
    
    if not resultados:
        return "El estudiante aún no ha rendido ningún cuestionario."
        
    respuesta = "Historial de Cuestionarios del estudiante:\n"
    for fila in resultados:
        respuesta += f"- Quiz ID {fila[0]} | Intento {fila[1]} | Estado: {fila[2]} | Nota: {fila[3]} | Tiempo: {fila[4]} min\n"
        
    return respuesta

@tool
def consultar_esfuerzo_scorm(estudiante_id: int) -> str:
    """
    Usa esta herramienta para revisar si el estudiante ha estudiado el material de clases (paquetes SCORM).
    Útil para la fase de 'Monitoreo' SRL, para saber si el alumno leyó la materia antes de hacer preguntas o evaluaciones.
    """
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
    conexion.close()
    
    if not resultados:
        return "El estudiante no ha abierto ningún material de estudio (SCORM) aún."
        
    respuesta = "Progreso de estudio del material (SCORM):\n"
    for fila in resultados:
        puntaje_texto = f"{fila[2]}%" if fila[2] is not None else "Sin calificar"
        respuesta += f"- Módulo SCORM {fila[0]} | Estado: {fila[1]} | Puntaje interno: {puntaje_texto}\n"
        
    return respuesta

tools = [consultar_rendimiento_cuestionarios, consultar_esfuerzo_scorm]