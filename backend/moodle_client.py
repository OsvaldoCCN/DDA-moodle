import requests
import os
from dotenv import load_dotenv

load_dotenv()

MOODLE_URL = os.getenv("MOODLE_URL") # ej: "https://tudominio.cl/webservice/rest/server.php"
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN")

def call_moodle_api(function_name, **kwargs):
    params = {
        "wstoken": MOODLE_TOKEN,
        "wsfunction": function_name,
        "moodlewsrestformat": "json"
    }
    params.update(kwargs)
    
    response = requests.post(MOODLE_URL, data=params)
    
    # Líneas de depuración para ver qué responde Moodle realmente
    print(f"Status Code: {response.status_code}")
    print(f"Respuesta cruda: {response.text[:500]}") 
    
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print("Error: La respuesta no pudo ser convertida a JSON.")
        return None

# Prueba rápida:
site_info = call_moodle_api("core_webservice_get_site_info")
print(site_info)