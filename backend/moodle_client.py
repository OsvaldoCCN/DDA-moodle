import os
import requests
import logging

logger = logging.getLogger(__name__)

def call_moodle_api(wsfunction, **kwargs):
    token = os.getenv("MOODLE_TOKEN")
    url_base = os.getenv("MOODLE_URL")
    
    if not token or not url_base:
        logger.error("Falta MOODLE_TOKEN o MOODLE_URL en las variables de entorno.")
        return None

    # Endpoint base
    endpoint = f"{url_base}/webservice/rest/server.php"
    
    # Parámetros base, FORZANDO siempre JSON
    payload = {
        "wstoken": token,
        "wsfunction": wsfunction,
        "moodlewsrestformat": "json"
    }
    
    # Añadimos los parámetros dinámicos (courseids, userid, etc.)
    payload.update(kwargs)
    
    try:
        response = requests.post(endpoint, data=payload)
        response.raise_for_status()
        
        # Intentamos parsear a JSON
        data = response.json()
        
        # Moodle devuelve código HTTP 200 incluso si hay un error lógico de token
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