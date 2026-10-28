import json
from moodle_client import call_moodle_api
from moodle_parser import MoodleSRLParser

ID_ALUMNO = 3
ID_SCORM = 1 

print(f"1. Buscando la estructura interna (SCO) del SCORM {ID_SCORM}...\n")
scoes_crudos = call_moodle_api("mod_scorm_get_scorm_scoes", scormid=ID_SCORM)

scoid_valido = None
if isinstance(scoes_crudos, dict) and "scoes" in scoes_crudos:
    for sco in scoes_crudos["scoes"]:
        if sco.get("scormtype") == "sco":
            scoid_valido = sco.get("id")
            break

if not scoid_valido:
    print("No se encontró un módulo SCO válido o Moodle devolvió un error.")
else:
    print(f"Componente SCO encontrado (ID: {scoid_valido})")
    print(f"2. Extrayendo la huella digital del alumno {ID_ALUMNO}...\n")
    

    raw_tracks = call_moodle_api(
        "mod_scorm_get_scorm_sco_tracks", 
        userid=ID_ALUMNO, 
        scoid=scoid_valido
    )
    

    datos_scorm = MoodleSRLParser.limpiar_tracking_scorm(raw_tracks)
    
    print(json.dumps(datos_scorm, indent=4, ensure_ascii=False))