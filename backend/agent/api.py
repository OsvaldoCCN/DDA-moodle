"""
API HTTP para el frontend. Ubicación: backend/agent/api.py (junto a graph.py, tools.py, etc.,
porque el proyecto usa imports planos como `from graph import app`).

Ejecutar (desde backend/agent):
    pip install fastapi uvicorn
    uvicorn api:api --reload --port 8000
"""
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from graph import app as grafo
from tools import obtener_conexion

logger = logging.getLogger(__name__)

NOTA_MAX = float(os.getenv("NOTA_MAX", "7"))          # escala de notas de tus cuestionarios
UMBRAL_NOTA = NOTA_MAX * 0.57                         # 57% (equivale a 4,0 en escala 1 a 7)
ESTADOS_SCORM_OK = {"completed", "passed", "completado"}
ESTADOS_QUIZ_OK = {"finished", "finalizado"}

api = FastAPI(title="Tutor Socrático SRL")
api.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginIn(BaseModel):
    estudiante_id: int
    course_id: Optional[int] = None


class ChatIn(BaseModel):
    estudiante_id: int
    course_id: int
    mensaje: str


def _consulta(sql: str, params: tuple = ()):
    con = obtener_conexion()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute(sql, params)
        filas = cur.fetchall()
        cur.close()
        return filas
    finally:
        con.close()


def _estudiante(estudiante_id: int) -> Dict[str, Any]:
    filas = _consulta("SELECT id, anon_id FROM estudiantes WHERE id = %s", (estudiante_id,))
    if not filas:
        raise HTTPException(status_code=404, detail="No existe un estudiante con ese ID.")
    return filas[0]


def _obtener_historial(estudiante_id: int, course_id: int) -> List[Dict[str, str]]:
    _estudiante(estudiante_id)
    filas = _consulta(
        """SELECT mensaje_usuario, respuesta_agente, contexto_srl_inyectado
           FROM interacciones_bot
           WHERE estudiante_id = %s AND moodle_courseid = %s
           ORDER BY id DESC LIMIT 20""",
        (estudiante_id, course_id),
    )
    salida = []
    for f in reversed(filas):
        salida.append({"rol": "user", "texto": f["mensaje_usuario"], "fase": ""})
        salida.append({"rol": "bot", "texto": f["respuesta_agente"], "fase": f["contexto_srl_inyectado"] or ""})
    return salida


@api.post("/api/login")
def login(datos: LoginIn):
    return _estudiante(datos.estudiante_id)


@api.get("/api/lad/{estudiante_id}")
def lad(estudiante_id: int, course_id: int = Query(..., description="ID del curso en Moodle (moodle_courseid)")):
    est = _estudiante(estudiante_id)

    # Catálogo de nombres de actividades del curso
    nombres_quiz: Dict[int, str] = {}
    nombres_scorm: Dict[int, str] = {}
    for act in _consulta(
        "SELECT tipo, instancia_id, nombre FROM actividades_curso WHERE moodle_courseid = %s",
        (course_id,),
    ):
        if act["tipo"] == "quiz":
            nombres_quiz[act["instancia_id"]] = act["nombre"]
        elif act["tipo"] == "scorm":
            nombres_scorm[act["instancia_id"]] = act["nombre"]

    # Cuestionarios: mejor nota por quiz en el curso
    quizzes: Dict[int, Dict[str, Any]] = {}
    for f in _consulta(
        """SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados
           FROM historico_cuestionarios
           WHERE estudiante_id = %s AND moodle_courseid = %s""",
        (estudiante_id, course_id),
    ):
        qid = f["moodle_quizid"]
        q = quizzes.setdefault(
            qid,
            {
                "quiz_id": qid,
                "nombre": nombres_quiz.get(qid, f"Quiz {qid}"),
                "mejor_nota": 0.0,
                "intentos": 0,
                "minutos": 0.0,
                "completado": False,
            },
        )
        q["mejor_nota"] = max(q["mejor_nota"], float(f["nota"] or 0))
        q["intentos"] += 1
        q["minutos"] += float(f["minutos_usados"] or 0)
        q["completado"] = q["completado"] or (f["estado"] or "").lower() in ESTADOS_QUIZ_OK
    quizzes_lista = sorted(quizzes.values(), key=lambda q: q["quiz_id"])

    # SCORM: tiempo sumado, mejor puntaje y estado del último intento por módulo en el curso
    scorm: Dict[int, Dict[str, Any]] = {}
    for f in _consulta(
        """SELECT moodle_scormid, numero_intento, estado, tiempo_invertido_segundos, puntaje
           FROM historico_scorm
           WHERE estudiante_id = %s AND moodle_courseid = %s
           ORDER BY moodle_scormid, numero_intento""",
        (estudiante_id, course_id),
    ):
        sid = f["moodle_scormid"]
        s = scorm.setdefault(
            sid,
            {"scorm_id": sid, "intentos": 0, "segundos": 0, "puntaje": 0.0, "completado": False},
        )
        s["intentos"] += 1
        s["segundos"] += int(f["tiempo_invertido_segundos"] or 0)
        s["puntaje"] = max(s["puntaje"], float(f["puntaje"] or 0))
        s["completado"] = (f["estado"] or "").lower() in ESTADOS_SCORM_OK  # el último intento manda
    scorm_lista = [
        {
            "scorm_id": s["scorm_id"],
            "nombre": nombres_scorm.get(s["scorm_id"], f"Módulo SCORM {s['scorm_id']}"),
            "intentos": s["intentos"],
            "minutos": round(s["segundos"] / 60),
            "puntaje": s["puntaje"],
            "completado": s["completado"],
        }
        for s in sorted(scorm.values(), key=lambda s: s["scorm_id"])
    ]

    # Metas de planeación del estudiante en el curso (si existen)
    metas_rows = _consulta(
        """SELECT meta_nota_porcentaje, meta_minutos_semanales
           FROM resumen_lad_estudiante
           WHERE estudiante_id = %s AND moodle_courseid = %s""",
        (estudiante_id, course_id),
    )
    meta_nota = float(metas_rows[0]["meta_nota_porcentaje"]) if metas_rows and metas_rows[0]["meta_nota_porcentaje"] is not None else 70.0
    meta_minutos = int(metas_rows[0]["meta_minutos_semanales"]) if metas_rows and metas_rows[0]["meta_minutos_semanales"] is not None else 60

    # Resumen calculado al vuelo para el curso
    notas = [q["mejor_nota"] for q in quizzes_lista]
    promedio = sum(notas) / len(notas) if notas else 0.0
    items = len(quizzes_lista) + len(scorm_lista)
    hechos = sum(1 for q in quizzes_lista if q["completado"]) + sum(1 for s in scorm_lista if s["completado"])
    progreso = round(hechos / items * 100) if items else 0
    if not items or promedio < NOTA_MAX * 0.64 or progreso < 50:
        riesgo = "alto" if items else "medio"
    elif promedio < NOTA_MAX * 0.76:
        riesgo = "medio"
    else:
        riesgo = "bajo"

    tiempo_scorm_min = sum(s["minutos"] for s in scorm_lista)
    tiempo_quiz_min = round(sum(q["minutos"] for q in quizzes_lista))

    return {
        "estudiante": est,
        "course_id": course_id,
        "resumen": {
            "promedio_quizzes": round(promedio, 1),
            "quizzes_completados": sum(1 for q in quizzes_lista if q["completado"]),
            "quizzes_total": len(quizzes_lista),
            "scorm_completados": sum(1 for s in scorm_lista if s["completado"]),
            "scorm_iniciados": len(scorm_lista),
            "tiempo_scorm_min": tiempo_scorm_min,
            "tiempo_total_min": tiempo_scorm_min + tiempo_quiz_min,
            "progreso": progreso,
            "riesgo": riesgo,
            "nota_max": NOTA_MAX,
            "meta_nota_porcentaje": meta_nota,
            "meta_minutos_semanales": meta_minutos,
        },
        "quizzes": [
            {
                "quiz_id": q["quiz_id"],
                "nombre": q["nombre"],
                "mejor_nota": q["mejor_nota"],
                "intentos": q["intentos"],
                "minutos": round(q["minutos"]),
                "completado": q["completado"],
            }
            for q in quizzes_lista
        ],
        "scorm": scorm_lista,
    }


@api.post("/api/chat")
def chat(datos: ChatIn):
    _estudiante(datos.estudiante_id)
    mensaje = datos.mensaje.strip()
    if not mensaje:
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")

    # Thread ID único por estudiante y curso para aislar sesiones en LangGraph
    thread_id = f"est_{datos.estudiante_id}_curso_{datos.course_id}"
    config = {"configurable": {"thread_id": thread_id}}

    estado_entrada = {
        "messages": [HumanMessage(content=mensaje)],
        "estudiante_id": datos.estudiante_id,
        "moodle_courseid": datos.course_id,
        "curso_id": datos.course_id,
        "tipo_interaccion": "reactiva",
        "user_message": mensaje,
    }

    try:
        nuevo = grafo.invoke(estado_entrada, config=config)
    except Exception as e:
        logger.exception("Falló el agente")
        raise HTTPException(status_code=502, detail="El tutor no pudo responder en este momento.") from e

    respuesta = nuevo["messages"][-1].content
    fase = nuevo.get("fase_srl_actual", "indefinida")
    juez = nuevo.get("evaluacion_juez", {}).get("estado", "aprobado")

    # Guarda la interacción aislada por estudiante y curso
    try:
        con = obtener_conexion()
        cur = con.cursor()
        cur.execute(
            """INSERT INTO interacciones_bot
               (estudiante_id, moodle_courseid, mensaje_usuario, respuesta_agente, contexto_srl_inyectado)
               VALUES (%s, %s, %s, %s, %s)""",
            (datos.estudiante_id, datos.course_id, mensaje, respuesta, fase),
        )
        con.commit()
        cur.close()
        con.close()
    except Exception:
        logger.exception("No se pudo guardar la interacción")

    return {"respuesta": respuesta, "fase": fase, "juez": juez}


@api.get("/api/chat/historial")
def chat_historial(
    estudiante_id: int = Query(..., description="ID del estudiante"),
    course_id: int = Query(..., description="ID del curso en Moodle"),
):
    return _obtener_historial(estudiante_id, course_id)


@api.get("/api/historial/{estudiante_id}")
def historial(
    estudiante_id: int,
    course_id: int = Query(..., description="ID del curso en Moodle"),
):
    return _obtener_historial(estudiante_id, course_id)


# Opcional: sirve el frontend desde el mismo servidor (http://localhost:8000). Debe ir al final.
_FRONT = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_FRONT):
    api.mount("/", StaticFiles(directory=_FRONT, html=True), name="frontend")
