import os
import requests
import logging

logger = logging.getLogger(__name__)

def call_moodle_api(wsfunction, **kwargs):
    token = os.getenv("MOODLE_TOKEN")
    print(f"Token en uso: {token}")
    url_base = os.getenv("MOODLE_URL")
    
    if not token or not url_base:
        logger.error("Falta MOODLE_TOKEN o MOODLE_URL en las variables de entorno.")
        return None

    endpoint = f"{url_base}/webservice/rest/server.php"
    
    payload = {
        "wstoken": token,
        "wsfunction": wsfunction,
        "moodlewsrestformat": "json"
    }
    
    # Transformación de parámetros para el estándar de Moodle
    for key, value in kwargs.items():
        if isinstance(value, (list, tuple)):
            # Convierte mi_lista=[A, B] en mi_lista[0]=A, mi_lista[1]=B
            for i, item in enumerate(value):
                payload[f"{key}[{i}]"] = item
        else:
            payload[key] = value
            
    try:
        response = requests.post(endpoint, data=payload)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, dict) and data.get("exception"):
            logger.error(f"Moodle API Exception [{data.get('errorcode')}]: {data.get('message')}")
            return None
            
        return data
        
    except ValueError:
        logger.error(f"La respuesta no es JSON válido. Respuesta cruda: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al conectar con Moodle: {e}")
        return None

def obtener_id_por_correo_en_curso(correo, course_id):
    usuarios = call_moodle_api(
        "core_enrol_get_enrolled_users",
        courseid=course_id
    )

    if not usuarios:
        logger.error(f"No se pudo obtener la lista de usuarios del curso {course_id}")
        return None

    for usuario in usuarios:
        if usuario.get("email") == correo:
            return usuario.get("id")

    logger.error(f"Estudiante con correo {correo} no encontrado en el curso {course_id}")
    return None