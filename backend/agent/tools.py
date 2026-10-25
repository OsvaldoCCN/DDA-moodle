import sqlite3
from langchain_core.tools import tool

DB_NAME = "srl_tesis.db"

@tool
def consultar_rendimiento_cuestionarios(estudiante_id: int) -> str:
    """
    Usa esta herramienta para consultar las notas y los intentos de un estudiante en sus cuestionarios.
    Útil cuando el estudiante pregunta por sus calificaciones o necesitas evaluar su fase de 'Desempeño' o 'Reflexión' SRL.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    cursor.execute('''
        SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados 
        FROM historico_cuestionarios 
        WHERE estudiante_id = ?
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
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()
    
    # Buscamos el último registro de cada SCORM para ver su estado final
    cursor.execute('''
        SELECT moodle_scormid, estado, puntaje, MAX(fecha_registro) 
        FROM historico_scorm 
        WHERE estudiante_id = ?
        GROUP BY moodle_scormid
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