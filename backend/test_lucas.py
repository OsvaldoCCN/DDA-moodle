from dotenv import load_dotenv
from moodle_client import call_moodle_api

load_dotenv()

LUCAS_MOODLE_ID = 4
SCORM_ID = 13  # Probemos con el SCORM 13 que vimos en la DB

print(f"🔍 [MODO PRODUCCIÓN] Obteniendo datos CMI de Lucas (ID {LUCAS_MOODLE_ID}) vía API REST...\n")

# 1. Obtener la lista de SCOs del paquete SCORM
# Usamos la función autorizada en tu Moodle: mod_scorm_get_scorm_scoes
res_scoes = call_moodle_api("mod_scorm_get_scorm_scoes", scormid=SCORM_ID)

if not res_scoes or "scoes" not in res_scoes:
    print("❌ No se pudieron obtener los SCOs del SCORM.")
    exit()

scoes = res_scoes["scoes"]
print(f"📦 Se encontraron {len(scoes)} objeto(s) SCO en el SCORM {SCORM_ID}.")

# 2. Consultar el tracking específico de Lucas en cada SCO
for sco in scoes:
    scoid = sco.get("id")
    print(f"\n--- Consultando SCO ID: {scoid} ---")
    
    # Aquí es donde le decimos a Moodle explícitamente: "Dame los datos del userid 4, intento 1"
    tracks = call_moodle_api(
        "mod_scorm_get_scorm_sco_tracks", 
        userid=LUCAS_MOODLE_ID, 
        scoid=scoid, 
        attempt=1
    )
    
    if tracks and "data" in tracks and "tracks" in tracks["data"]:
        print("✅ ¡Datos CMI recuperados por la API!")
        for track in tracks["data"]["tracks"]:
            element = track.get("element")
            value = track.get("value")
            
            # Filtramos para mostrar lo más importante para el LAD
            if element in ["cmi.core.lesson_status", "cmi.suspend_data", "cmi.core.score.raw", "cmi.core.total_time"]:
                print(f"  👉 {element}: {value}")
    else:
        print("  ⚠️ Sin datos de tracking para este SCO.")