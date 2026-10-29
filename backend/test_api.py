import os
import requests
from dotenv import load_dotenv

def probar_conexion():
    print("--- PASO 1: Leyendo variables de entorno ---")
    # Forzamos la lectura del archivo .env local
    load_dotenv(override=True)
    
    url_base = os.getenv("MOODLE_URL")
    token = os.getenv("MOODLE_TOKEN")
    
    # Imprimimos entre símbolos > < para detectar si hay espacios ocultos o comillas extrañas
    print(f"URL cargada:   >{url_base}<")
    print(f"Token cargado: >{token}<")
    
    if not url_base or not token:
        print("❌ ERROR: No se encontró MOODLE_URL o MOODLE_TOKEN en el archivo .env")
        return

    print("\n--- PASO 2: Enviando petición a Moodle ---")
    endpoint = f"{url_base}/webservice/rest/server.php"
    
    # core_webservice_get_site_info solo te devuelve información del sistema si el token es válido
    payload = {
        "wstoken": token,
        "wsfunction": "core_webservice_get_site_info",
        "moodlewsrestformat": "json"
    }
    
    print(f"Haciendo POST a: {endpoint}")
    
    try:
        response = requests.post(endpoint, data=payload)
        print(f"Status HTTP: {response.status_code}")
        print(f"Respuesta cruda (primeros 250 caracteres):\n{response.text[:250]}\n")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al intentar conectar: {e}")
        return

    print("--- PASO 3: Analizando respuesta JSON ---")
    try:
        data = response.json()
        
        # Moodle devuelve un diccionario con 'exception' si falla, a pesar de usar json
        if isinstance(data, dict) and "exception" in data:
            print("❌ Moodle rechazó la petición:")
            print(f"   Código de error: {data.get('errorcode')}")
            print(f"   Mensaje: {data.get('message')}")
        else:
            print("✅ ¡ÉXITO! Moodle validó tu token correctamente.")
            print(f"   Conectado al sitio: {data.get('sitename')}")
            print(f"   Usuario asociado al token: {data.get('fullname')}")
            
    except ValueError:
        print("❌ ERROR FATAL: La respuesta no es un JSON. Moodle devolvió XML o HTML.")

if __name__ == "__main__":
    probar_conexion()