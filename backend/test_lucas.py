import json
from dotenv import load_dotenv
from moodle_client import call_moodle_api

load_dotenv()

USER_MOODLE_ID = 4
COURSE_ID = 5  # Curso donde vimos el quiz 19

print(f"🔍 [MODO PRODUCCIÓN] Obteniendo datos de Quizzes (Curso {COURSE_ID}, Usuario {USER_MOODLE_ID})...\n")

# 1. Obtener la lista de quizzes del curso (para ver puntaje máximo: sumgrades y grade)
res_quizzes = call_moodle_api("mod_quiz_get_quizzes_by_courses", courseids=[COURSE_ID])

if not res_quizzes or "quizzes" not in res_quizzes:
    print("❌ No se pudieron obtener los quizzes del curso.")
    exit()

quizzes = res_quizzes["quizzes"]
print(f"📦 Se encontraron {len(quizzes)} quiz(zes) en el curso {COURSE_ID}.")

# 2. Consultar los intentos del usuario en cada quiz
for quiz in quizzes:
    quiz_id = quiz.get("id")
    print(f"\n--- Quiz ID: {quiz_id} | Nombre: {quiz.get('name')} ---")
    print(f"  📊 Definición del Quiz -> sumgrades (suma preguntas): {quiz.get('sumgrades')} | grade (nota máxima escala): {quiz.get('grade')}")

    # status="all" trae tanto intentos finalizados como en progreso
    res_attempts = call_moodle_api(
        "mod_quiz_get_user_attempts",
        quizid=quiz_id,
        userid=USER_MOODLE_ID,
        status="all"
    )

    if res_attempts and res_attempts.get("attempts"):
        print(f"  ✅ {len(res_attempts['attempts'])} intento(s) encontrado(s):")
        for intento in res_attempts["attempts"]:
            print(json.dumps(intento, indent=4, ensure_ascii=False))
    else:
        print("  ⚠️ Sin intentos registrados para este usuario en este quiz.")