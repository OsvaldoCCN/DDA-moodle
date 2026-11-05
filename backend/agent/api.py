"""
API HTTP para el frontend. Ubicación: backend/agent/api.py (junto a graph.py, tools.py, etc.,
porque el proyecto usa imports planos como `from graph import app`).

Ejecutar (desde backend/agent):
    pip install fastapi uvicorn
    uvicorn api:api --reload --port 8000
"""
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
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

# Estado de conversación por estudiante (igual que ESTADO_ACTUAL en main.py). Se pierde al reiniciar el servidor.
SESIONES: Dict[int, Dict[str, Any]] = {}


class LoginIn(BaseModel):
    estudiante_id: int


class ChatIn(BaseModel):
    estudiante_id: int
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


@api.post("/api/login")
def login(datos: LoginIn):
    return _estudiante(datos.estudiante_id)


@api.get("/api/lad/{estudiante_id}")
def lad(estudiante_id: int):
    est = _estudiante(estudiante_id)

    # Cuestionarios: mejor nota por quiz
    quizzes: Dict[int, Dict[str, Any]] = {}
    for f in _consulta(
        "SELECT moodle_quizid, numero_intento, estado, nota FROM historico_cuestionarios WHERE estudiante_id = %s",
        (estudiante_id,),
    ):
        q = quizzes.setdefault(f["moodle_quizid"], {"quiz_id": f["moodle_quizid"], "mejor_nota": 0.0, "intentos": 0, "ok": False})
        q["mejor_nota"] = max(q["mejor_nota"], float(f["nota"] or 0))
        q["intentos"] += 1
        q["ok"] = q["ok"] or (f["estado"] or "").lower() in ESTADOS_QUIZ_OK
    quizzes_lista = sorted(quizzes.values(), key=lambda q: q["quiz_id"])

    # SCORM: tiempo sumado, mejor puntaje y estado del último intento por módulo
    scorm: Dict[int, Dict[str, Any]] = {}
    for f in _consulta(
        """SELECT moodle_scormid, numero_intento, estado, tiempo_invertido_segundos, puntaje
           FROM historico_scorm WHERE estudiante_id = %s ORDER BY moodle_scormid, numero_intento""",
        (estudiante_id,),
    ):
        s = scorm.setdefault(f["moodle_scormid"], {"scorm_id": f["moodle_scormid"], "segundos": 0, "puntaje": 0.0, "completado": False})
        s["segundos"] += int(f["tiempo_invertido_segundos"] or 0)
        s["puntaje"] = max(s["puntaje"], float(f["puntaje"] or 0))
        s["completado"] = (f["estado"] or "").lower() in ESTADOS_SCORM_OK  # el último intento manda
    scorm_lista = [
        {"scorm_id": s["scorm_id"], "nombre": f"Módulo SCORM {s['scorm_id']}", "minutos": round(s["segundos"] / 60),
         "puntaje": s["puntaje"], "completado": s["completado"]}
        for s in sorted(scorm.values(), key=lambda s: s["scorm_id"])
    ]

    # Resumen (se calcula al vuelo; la tabla resumen_lad_estudiante no la llena el sincronizador)
    notas = [q["mejor_nota"] for q in quizzes_lista]
    promedio = sum(notas) / len(notas) if notas else 0.0
    items = len(quizzes_lista) + len(scorm_lista)
    hechos = sum(1 for q in quizzes_lista if q["ok"]) + sum(1 for s in scorm_lista if s["completado"])
    progreso = round(hechos / items * 100) if items else 0
    if not items or promedio < NOTA_MAX * 0.64 or progreso < 50:
        riesgo = "alto" if items else "medio"
    elif promedio < NOTA_MAX * 0.76:
        riesgo = "medio"
    else:
        riesgo = "bajo"

    return {
        "estudiante": est,
        "resumen": {
            "promedio_quizzes": round(promedio, 1),
            "quizzes_completados": sum(1 for q in quizzes_lista if q["ok"]),
            "quizzes_total": len(quizzes_lista),
            "tiempo_scorm_min": sum(s["minutos"] for s in scorm_lista),
            "progreso": progreso,
            "riesgo": riesgo,
            "nota_max": NOTA_MAX,
        },
        "quizzes": [{"quiz_id": q["quiz_id"], "mejor_nota": q["mejor_nota"], "intentos": q["intentos"]} for q in quizzes_lista],
        "scorm": scorm_lista,
    }


@api.post("/api/chat")
def chat(datos: ChatIn):
    _estudiante(datos.estudiante_id)
    mensaje = datos.mensaje.strip()
    if not mensaje:
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")

    estado = SESIONES.setdefault(datos.estudiante_id, {
        "messages": [],
        "estudiante_id": datos.estudiante_id,
        "fase_srl_actual": "indefinida",
        "contexto_academico": {},
        "tipo_interaccion": "reactiva",
        "user_message": "",
    })
    estado["messages"].append(HumanMessage(content=mensaje))
    estado["user_message"] = mensaje

    try:
        nuevo = grafo.invoke(estado)
    except Exception as e:
        logger.exception("Falló el agente")
        raise HTTPException(status_code=502, detail="El tutor no pudo responder en este momento.") from e

    SESIONES[datos.estudiante_id] = nuevo
    respuesta = nuevo["messages"][-1].content
    fase = nuevo.get("fase_srl_actual", "indefinida")
    juez = nuevo.get("evaluacion_juez", {}).get("estado", "aprobado")

    # Guarda la interacción en la tabla que ya existe en el esquema
    try:
        con = obtener_conexion()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO interacciones_bot (estudiante_id, mensaje_usuario, respuesta_agente, contexto_srl_inyectado) VALUES (%s, %s, %s, %s)",
            (datos.estudiante_id, mensaje, respuesta, fase),
        )
        con.commit()
        cur.close()
        con.close()
    except Exception:
        logger.exception("No se pudo guardar la interacción")

    return {"respuesta": respuesta, "fase": fase, "juez": juez}


@api.get("/api/historial/{estudiante_id}")
def historial(estudiante_id: int):
    _estudiante(estudiante_id)
    filas = _consulta(
        """SELECT mensaje_usuario, respuesta_agente, contexto_srl_inyectado
           FROM interacciones_bot WHERE estudiante_id = %s ORDER BY id DESC LIMIT 20""",
        (estudiante_id,),
    )
    salida = []
    for f in reversed(filas):
        salida.append({"rol": "user", "texto": f["mensaje_usuario"], "fase": ""})
        salida.append({"rol": "bot", "texto": f["respuesta_agente"], "fase": f["contexto_srl_inyectado"] or ""})
    return salida


# Opcional: sirve el frontend desde el mismo servidor (http://localhost:8000). Debe ir al final.
_FRONT = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_FRONT):
    api.mount("/", StaticFiles(directory=_FRONT, html=True), name="frontend")
