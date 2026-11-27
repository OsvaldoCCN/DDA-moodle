import logging
import os
import json
from datetime import datetime
import mysql.connector
from langchain_core.tools import tool

from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_PORT,
)

logger = logging.getLogger(__name__)

NOTA_MAX = float(os.getenv("NOTA_MAX", "7"))
ESTADOS_SCORM_OK = {"completed", "passed", "completado"}
ESTADOS_QUIZ_OK = {"finished", "finalizado"}


def obtener_conexion():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset="utf8mb4",
        use_unicode=True,
    )


def _cargar_nombres_actividades(cursor, moodle_courseid: int) -> tuple[dict, dict]:
    """Obtiene el catálogo de nombres y fechas de cierre de actividades del curso."""
    cursor.execute(
        """SELECT tipo, instancia_id, nombre, fecha_cierre
           FROM actividades_curso
           WHERE moodle_courseid = %s""",
        (moodle_courseid,),
    )
    quizzes = {}
    scorms = {}
    for tipo, instancia_id, nombre, fecha_cierre in cursor.fetchall():
        info = {"nombre": nombre, "fecha_cierre": fecha_cierre or 0}
        if tipo == "quiz":
            quizzes[instancia_id] = info
        elif tipo == "scorm":
            scorms[instancia_id] = info
    return quizzes, scorms


@tool
def consultar_lad_estudiante(estudiante_id: int, moodle_courseid: int) -> str:
    """
    Usa esta herramienta para ver el Panel de Aprendizaje (LAD) completo que el estudiante ve en su pantalla:
    KPIs generales (SCORMs completados, cuestionarios completados, promedio de notas, tiempo total de estudio,
    porcentaje de progreso, nivel de riesgo SRL, metas de planeación) y el resumen de cada actividad con su nombre.
    Úsala siempre que el estudiante pregunte por su panel, resumen, avance general, metas, o cómo va en el curso.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor_cat = conexion.cursor()
        nombres_quiz, nombres_scorm = _cargar_nombres_actividades(
            cursor_cat, moodle_courseid
        )
        cursor_cat.close()

        cursor = conexion.cursor(dictionary=True)

        # Cuestionarios
        cursor.execute(
            """SELECT moodle_quizid, numero_intento, estado, nota, nota_maxima, minutos_usados, fecha_registro
               FROM historico_cuestionarios
               WHERE estudiante_id = %s AND moodle_courseid = %s
               ORDER BY moodle_quizid, numero_intento""",
            (estudiante_id, moodle_courseid),
        )
        quizzes = {}
        for f in cursor.fetchall():
            qid = f["moodle_quizid"]
            info_act = nombres_quiz.get(qid, {})
            q = quizzes.setdefault(
                qid,
                {
                    "quiz_id": qid,
                    "nombre": info_act.get("nombre", f"Quiz {qid}"),
                    "fecha_cierre": info_act.get("fecha_cierre", 0),
                    "mejor_nota": 0.0,
                    "nota_maxima": float(f["nota_maxima"] or NOTA_MAX),
                    "intentos": 0,
                    "minutos": 0.0,
                    "completado": False,
                    "ultima_fecha": None,
                },
            )
            q["mejor_nota"] = max(q["mejor_nota"], float(f["nota"] or 0))
            if f["nota_maxima"]:
                q["nota_maxima"] = float(f["nota_maxima"])
            q["intentos"] += 1
            q["minutos"] += float(f["minutos_usados"] or 0)
            q["completado"] = q["completado"] or (f["estado"] or "").lower() in ESTADOS_QUIZ_OK
            if f["fecha_registro"]:
                q["ultima_fecha"] = f["fecha_registro"]
        quizzes_lista = sorted(quizzes.values(), key=lambda x: x["quiz_id"])

        # SCORMs
        cursor.execute(
            """SELECT moodle_scormid, numero_intento, estado, tiempo_invertido_segundos, puntaje, fecha_registro
               FROM historico_scorm
               WHERE estudiante_id = %s AND moodle_courseid = %s
               ORDER BY moodle_scormid, numero_intento""",
            (estudiante_id, moodle_courseid),
        )
        scorm = {}
        for f in cursor.fetchall():
            sid = f["moodle_scormid"]
            info_act = nombres_scorm.get(sid, {})
            s = scorm.setdefault(
                sid,
                {
                    "scorm_id": sid,
                    "nombre": info_act.get("nombre", f"Módulo SCORM {sid}"),
                    "intentos": 0,
                    "segundos": 0,
                    "puntaje": 0.0,
                    "completado": False,
                    "ultima_fecha": None,
                },
            )
            s["intentos"] += 1
            s["segundos"] += int(f["tiempo_invertido_segundos"] or 0)
            s["puntaje"] = max(s["puntaje"], float(f["puntaje"] or 0))
            s["completado"] = (f["estado"] or "").lower() in ESTADOS_SCORM_OK
            if f["fecha_registro"]:
                s["ultima_fecha"] = f["fecha_registro"]
        scorm_lista = sorted(scorm.values(), key=lambda x: x["scorm_id"])

        cursor.close()

        # Cálculos idénticos a api.py (GET /api/lad)
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

        tiempo_scorm_min = sum(round(s["segundos"] / 60) for s in scorm_lista)
        tiempo_quiz_min = round(sum(q["minutos"] for q in quizzes_lista))
        tiempo_total_min = tiempo_scorm_min + tiempo_quiz_min

        lines = [
            f"=== PANEL LAD DEL ESTUDIANTE {estudiante_id} (CURSO {moodle_courseid}) ===",
            f"- Material interactivo (SCORM) completado: {sum(1 for s in scorm_lista if s['completado'])}/{len(scorm_lista)}",
            f"- Cuestionarios completados: {sum(1 for q in quizzes_lista if q['completado'])}/{len(quizzes_lista)}",
            f"- Promedio en cuestionarios: {promedio:.1f}",
            f"- Tiempo total de estudio: {tiempo_total_min} min (SCORM: {tiempo_scorm_min} min, Quizzes: {tiempo_quiz_min} min)",
            f"- Progreso general del curso: {progreso}% | Nivel de riesgo SRL: {riesgo}",
            "",
            "Detalle de Cuestionarios en el LAD:",
        ]
        if not quizzes_lista:
            lines.append("  (Sin cuestionarios registrados aún)")
        for q in quizzes_lista:
            estado_txt = "Completado" if q["completado"] else "Sin completar"
            fecha_txt = q["ultima_fecha"].strftime("%Y-%m-%d %H:%M") if q["ultima_fecha"] else "N/A"
            cierre_txt = (
                datetime.fromtimestamp(q["fecha_cierre"]).strftime("%Y-%m-%d %H:%M")
                if q["fecha_cierre"] and q["fecha_cierre"] > 0
                else "Sin cierre"
            )
            lines.append(
                f"  * {q['nombre']} (ID {q['quiz_id']}): Mejor nota {q['mejor_nota']:.1f}/{q['nota_maxima']:.1f} | "
                f"{q['intentos']} intento(s) | {round(q['minutos'])} min | {estado_txt} | "
                f"Última actividad: {fecha_txt} | Cierre: {cierre_txt}"
            )

        lines.append("")
        lines.append("Detalle de Material Interactivo (SCORM) en el LAD:")
        if not scorm_lista:
            lines.append("  (Sin módulos SCORM registrados aún)")
        for s in scorm_lista:
            estado_txt = "Completado" if s["completado"] else "En progreso"
            fecha_txt = s["ultima_fecha"].strftime("%Y-%m-%d %H:%M") if s["ultima_fecha"] else "N/A"
            lines.append(
                f"  * {s['nombre']} (ID {s['scorm_id']}): {estado_txt} | Puntaje {s['puntaje']:.0f}% | "
                f"{s['intentos']} intento(s) | {round(s['segundos'] / 60)} min | Última actividad: {fecha_txt}"
            )

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error al consultar LAD para estudiante {estudiante_id}, curso {moodle_courseid}: {e}")
        return f"No se pudo consultar el panel LAD debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()


@tool
def consultar_rendimiento_cuestionarios(estudiante_id: int, moodle_courseid: int) -> str:
    """
    Usa esta herramienta para consultar el detalle intento por intento de los cuestionarios de un estudiante en un curso específico.
    Útil cuando el estudiante pregunta por notas específicas, intentos previos o tiempo usado en cuestionarios.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        nombres_quiz, _ = _cargar_nombres_actividades(cursor, moodle_courseid)

        cursor.execute('''
            SELECT moodle_quizid, numero_intento, estado, nota, minutos_usados, fecha_registro
            FROM historico_cuestionarios 
            WHERE estudiante_id = %s AND moodle_courseid = %s
            ORDER BY moodle_quizid, numero_intento DESC
        ''', (estudiante_id, moodle_courseid))
        
        resultados = cursor.fetchall()
        cursor.close()
        
        if not resultados:
            return f"El estudiante aún no ha rendido ningún cuestionario en el curso {moodle_courseid}."
            
        respuesta = f"Historial de Cuestionarios del estudiante ID {estudiante_id} (Curso {moodle_courseid}):\n"
        for fila in resultados:
            qid = fila[0]
            nombre = nombres_quiz.get(qid, {}).get("nombre", f"Quiz ID {qid}")
            nota_str = f"{fila[3]:.1f}" if fila[3] is not None else "Sin nota"
            minutos_str = f"{fila[4]:.1f}" if fila[4] is not None else "N/A"
            fecha_str = fila[5].strftime("%Y-%m-%d %H:%M") if fila[5] else "N/A"
            respuesta += f"- {nombre} (ID {qid}) | Intento {fila[1]} | Estado: {fila[2]} | Nota: {nota_str} | Tiempo: {minutos_str} min | Fecha: {fecha_str}\n"
            
        return respuesta
    except Exception as e:
        logger.error(f"Error al consultar cuestionarios para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el rendimiento de cuestionarios debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()


@tool
def consultar_esfuerzo_scorm(estudiante_id: int, moodle_courseid: int) -> str:
    """
    Usa esta herramienta para revisar si el estudiante ha estudiado el material interactivo (SCORM) de un curso específico, 
    cuántos intentos realizó y en qué preguntas específicas se equivocó leyendo el suspend_data JSON.
    Útil para la fase de 'Monitoreo' o 'Reflexión' SRL.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        _, nombres_scorm = _cargar_nombres_actividades(cursor, moodle_courseid)
        
        cursor.execute('''
            SELECT moodle_scormid, numero_intento, estado, puntaje, suspend_data, tiempo_invertido_segundos, fecha_registro
            FROM historico_scorm 
            WHERE estudiante_id = %s AND moodle_courseid = %s
            ORDER BY moodle_scormid, numero_intento ASC
        ''', (estudiante_id, moodle_courseid))
        
        resultados = cursor.fetchall()
        cursor.close()
        
        if not resultados:
            return f"El estudiante no registra interacciones en paquetes de contenido (SCORM) en el curso {moodle_courseid} aún."
            
        respuesta = f"Progreso detallado del material interactivo (SCORM) para estudiante ID {estudiante_id} (Curso {moodle_courseid}):\n"
        
        for fila in resultados:
            scorm_id = fila[0]
            nombre = nombres_scorm.get(scorm_id, {}).get("nombre", f"Módulo SCORM {scorm_id}")
            intento = fila[1]
            estado = fila[2]
            puntaje = f"{fila[3]}%" if fila[3] is not None else "Sin calificar"
            json_respuestas = fila[4]
            tiempo = fila[5]
            fecha_str = fila[6].strftime("%Y-%m-%d %H:%M") if fila[6] else "N/A"
            
            respuesta += f"\n- {nombre} (ID {scorm_id}, Intento {intento}) | Estado: {estado} | Tiempo: {tiempo}s | Puntaje: {puntaje} | Fecha: {fecha_str}\n"
            
            if json_respuestas:
                try:
                    datos_json = json.loads(json_respuestas)
                    if isinstance(datos_json, dict):
                        pantalla = datos_json.get("pantalla")
                        key = datos_json.get("key")
                        if pantalla or key:
                            respuesta += f"  Contexto SCORM: key={key or '-'} | pantalla={pantalla or '-'}\n"

                        results = datos_json.get("results")
                        answers = datos_json.get("answers")

                        if isinstance(results, dict) and results:
                            respuesta += "  Resultados por pregunta en este intento:\n"
                            for pregunta_id, ok in results.items():
                                estado_p = "Correcta" if ok else "Incorrecta"
                                resp_txt = answers.get(pregunta_id) if isinstance(answers, dict) else None
                                extra = f" (respuesta marcada: {resp_txt})" if resp_txt is not None else ""
                                respuesta += f"    * {pregunta_id}: {estado_p}{extra}\n"
                        elif isinstance(answers, dict) and answers:
                            respuesta += "  Respuestas específicas del alumno en este intento:\n"
                            for pregunta_id, datos_respuesta in answers.items():
                                if isinstance(datos_respuesta, dict):
                                    correcta = "Correcta (ok:true)" if datos_respuesta.get("ok") else "Incorrecta (ok:false)"
                                    respuesta += f"    * {pregunta_id}: {correcta}\n"
                                else:
                                    respuesta += f"    * {pregunta_id}: {datos_respuesta}\n"
                        else:
                            respuesta += f"  Datos internos guardados: {json_respuestas}\n"
                    else:
                        respuesta += f"  Datos internos guardados: {json_respuestas}\n"
                except json.JSONDecodeError:
                    respuesta += f"  Datos internos guardados: {json_respuestas}\n"
            else:
                respuesta += "  No hay registro de respuestas específicas guardadas.\n"
                
        return respuesta
    except Exception as e:
        logger.error(f"Error al consultar SCORM para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el progreso de SCORM debido a un error de conexión: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()


@tool
def consultar_historial_conversaciones(
    estudiante_id: int,
    moodle_courseid: int,
    limite: int = 10,
    palabra_clave: str = "",
) -> str:
    """
    Usa esta herramienta para revisar conversaciones de sesiones anteriores con el estudiante en este curso.
    Útil cuando el estudiante menciona algo que hablaron antes (por ejemplo, una meta previa, un plan de estudio,
    dudas pasadas o "como te dije la vez pasada"). Puedes filtrar opcionalmente por palabra_clave.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        limite_seguro = max(1, min(int(limite or 10), 25))
        kw = (palabra_clave or "").strip()

        if kw:
            like = f"%{kw}%"
            cursor.execute(
                """SELECT mensaje_usuario, respuesta_agente, contexto_srl_inyectado, fecha_hora
                   FROM interacciones_bot
                   WHERE estudiante_id = %s AND moodle_courseid = %s
                     AND (mensaje_usuario LIKE %s OR respuesta_agente LIKE %s)
                   ORDER BY id DESC LIMIT %s""",
                (estudiante_id, moodle_courseid, like, like, limite_seguro),
            )
        else:
            cursor.execute(
                """SELECT mensaje_usuario, respuesta_agente, contexto_srl_inyectado, fecha_hora
                   FROM interacciones_bot
                   WHERE estudiante_id = %s AND moodle_courseid = %s
                   ORDER BY id DESC LIMIT %s""",
                (estudiante_id, moodle_courseid, limite_seguro),
            )

        filas = cursor.fetchall()
        cursor.close()

        if not filas:
            if kw:
                return f"No se encontraron conversaciones previas del estudiante {estudiante_id} en el curso {moodle_courseid} con '{kw}'."
            return f"No hay conversaciones previas registradas para el estudiante {estudiante_id} en el curso {moodle_courseid}."

        lineas = [
            f"Historial de sesiones anteriores (Estudiante {estudiante_id}, Curso {moodle_courseid}):"
        ]
        for f in reversed(filas):
            fecha_txt = f["fecha_hora"].strftime("%Y-%m-%d %H:%M") if f["fecha_hora"] else "N/A"
            fase_txt = f["contexto_srl_inyectado"] or "indefinida"
            lineas.append(f"[{fecha_txt} | Fase: {fase_txt}]")
            lineas.append(f"  Estudiante: {f['mensaje_usuario']}")
            lineas.append(f"  Tutor: {f['respuesta_agente']}")

        return "\n".join(lineas)
    except Exception as e:
        logger.error(f"Error al consultar historial para estudiante {estudiante_id}: {e}")
        return f"No se pudo consultar el historial de conversaciones debido a un error: {str(e)}"
    finally:
        if conexion and conexion.is_connected():
            conexion.close()


tools = [
    consultar_lad_estudiante,
    consultar_rendimiento_cuestionarios,
    consultar_esfuerzo_scorm,
    consultar_historial_conversaciones,
]
