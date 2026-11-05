import os
import logging
from dotenv import load_dotenv
from moodle_client import call_moodle_api

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def testear_matriculados_curso():
    curso_id = 3
    logger.info(f"Consultando estudiantes matriculados en el Curso ID: {curso_id}...")

    # Llamada directa a la función que ya tienes aprobada en Moodle
    usuarios = call_moodle_api("core_enrol_get_enrolled_users", courseid=curso_id)

    if usuarios is None:
        logger.error("❌ Error al llamar a 'core_enrol_get_enrolled_users'.")
        return

    if not usuarios:
        print(f"⚠️ No se encontraron usuarios matriculados en el curso {curso_id}.")
    else:
        print(f"\n✅ Se encontraron {len(usuarios)} usuario(s) en el Curso ID {curso_id}:\n")
        print(f"{'ID Moodle':<12} | {'Nombre Completo':<25} | {'Correo Electrónico'}")
        print("-" * 65)
        
        for u in usuarios:
            moodle_id = u.get('id')
            nombre = u.get('fullname', 'Sin nombre')
            email = u.get('email', 'Sin correo')
            print(f"{str(moodle_id):<12} | {nombre:<25} | {email}")

if __name__ == "__main__":
    testear_matriculados_curso()