import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from llm import llm
from tools import tools

logger = logging.getLogger(__name__)

tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)

def gatekeeper_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guardián de entrada: Filtra solicitudes fuera de ámbito o intentos de trampa.
    """
    mensaje = state.get("user_message", "")
    
    prompt_guardrail = f"""Eres el guardián de entrada (Gatekeeper) de un tutor socrático universitario.
Tu tarea es analizar el mensaje del estudiante y decidir si la consulta es una petición válida para guiar su aprendizaje.

CONSULTAS VÁLIDAS (Debe ser aprobado):
- Consultar su tablero, panel, LAD, dashboard, desempeño, notas, progreso, avance, tiempo de estudio, metas, actividades realizadas (SCORM o cuestionarios), intentos, fechas o estado general en el curso (ej: "¿qué ves de mi tablero?", "¿cómo me ha ido?", "¿cuántos scorms he hecho?", "¿cuáles son mis notas?", "en el scorm X ¿puedes ver mi rendimiento?").
- Pedir aclaraciones o cuestionar datos que el tutor mencionó en su respuesta anterior (ej: "¿de dónde sacas que tengo 2/7?", "¿por qué dices eso?", "explícame ese cálculo").
- Dudas conceptuales, organización del tiempo, estrategias de estudio, sesiones anteriores y reflexión metacognitiva.

CONSULTAS INVÁLIDAS / TRAMPA / FUERA DE ÁMBITO (Debe ser rechazado):
- Pedir que el tutor resuelva directamente un ejercicio, examen, tarea o programe código por ellos.
- Temas completamente ajenos a la universidad o al ámbito académico.

Último mensaje del estudiante: "{mensaje}"

REGLA ESTRICTA: Responde ÚNICAMENTE con la palabra "valido" o "invalido"."""

    respuesta = llm.invoke([SystemMessage(content=prompt_guardrail)])
    decision = respuesta.content.strip().lower()
    
    if "invalido" in decision:
        mensaje_rechazo = AIMessage(
            content="Lo siento, pero mi rol como tutor socrático es guiar tu proceso de aprendizaje y autorregulación, no resolver ejercicios ni tareas por ti. ¿Cómo prefieres que abordemos este problema paso a paso?",
            name="gatekeeper_rejected"
        )
        return {
            "messages": [mensaje_rechazo],
            "es_valido": False
        }
    
    return {
        "es_valido": True
    }

def srl_classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clasifica la interacción según el modelo de Aprendizaje Autorregulado (SRL).
    """
    mensaje = state.get("user_message", "")

    prompt_clasificador = f"""Eres un experto pedagógico en el modelo de Aprendizaje Autorregulado (SRL).
Clasifica la intención del estudiante en una de las siguientes tres fases:
1. planificacion (organizar tiempo, fijación de metas, estructurar plan de estudio).
2. monitoreo (consultar progreso actual, revisar notas/rendimiento, seguimiento de lecturas o cuestionarios).
3. reflexion (análisis post-evaluación, autoevaluación, relación esfuerzo vs resultados).

Último mensaje del estudiante: "{mensaje}"

Si la consulta es sobre su avance o estado en el curso, clasifícala siempre como 'monitoreo'.
REGLA ESTRICTA: Responde ÚNICAMENTE con una palabra en minúsculas: planificacion, monitoreo, reflexion o indefinida."""

    respuesta_llm = llm.invoke([SystemMessage(content=prompt_clasificador)])
    
    fase_detectada = respuesta_llm.content.strip().lower()
    fase_detectada = fase_detectada.replace(".", "").replace("'", "").replace('"', "")
    
    fases_validas = ["planificacion", "monitoreo", "reflexion", "indefinida"]
    fase_final = "indefinida"
    
    for fase in fases_validas:
        if fase in fase_detectada:
            fase_final = fase
            break
            
    return {"fase_srl_actual": fase_final}

def data_orchestrator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evalúa si se deben consultar herramientas de base de datos según la pregunta del usuario.
    """
    historial = state.get("messages", [])
    fase = state.get("fase_srl_actual", "indefinida")
    estudiante_id = state.get("estudiante_id", 1)
    moodle_courseid = state.get("moodle_courseid") or state.get("curso_id") or 3
    
    prompt_orquestador = f"""Eres el orquestador de datos de un tutor socrático.
Fase SRL actual del estudiante: {fase}
ID del estudiante: {estudiante_id}
ID del curso (moodle_courseid): {moodle_courseid}

Tu tarea: Revisa la consulta del estudiante en el historial y decide qué herramientas de base de datos necesitas consultar:
- Usa 'consultar_lad_estudiante' si pregunta por su panel, resumen, avance general, promedio, riesgo, metas o "¿cómo voy?" en el curso.
- Usa 'consultar_rendimiento_cuestionarios' si pregunta por el detalle de intentos o notas de cuestionarios.
- Usa 'consultar_esfuerzo_scorm' si pregunta por avance de lectura, material interactivo o en qué preguntas específicas se equivocó.
- Usa 'consultar_historial_conversaciones' si menciona algo de una sesión anterior (ej. una meta acordada antes, un tema previo o "¿qué hablamos la última vez?").

Puedes invocar una o varias herramientas en paralelo pasando SIEMPRE estudiante_id={estudiante_id} y moodle_courseid={moodle_courseid}.
Si no requiere datos académicos, NO invoques ninguna herramienta."""

    mensajes = [SystemMessage(content=prompt_orquestador)] + historial
    respuesta = llm_with_tools.invoke(mensajes)
    
    if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
        return {"messages": [respuesta]}
    
    return {}

def generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera la respuesta pedagógica socrática adaptada a la fase SRL y al contexto obtenido.
    """
    historial = state.get("messages", [])
    fase = state.get("fase_srl_actual", "indefinida")
    
    if fase == "planificacion":
        personalidad = "Adoptas un tono empático y organizador. Tu meta es reducir la desorientación y ayudar a estructurar metas de tiempo y prioridades."
    elif fase == "monitoreo":
        personalidad = "Adoptas un tono analítico e interpelante. Tu meta es dar significado pedagógico al avance de estudio o lectura de materiales."
    elif fase == "reflexion":
        personalidad = "Adoptas un tono de espejo crítico. Tu meta es contrastar el esfuerzo del alumno con sus calificaciones para evaluar sus hábitos de estudio."
    else:
        personalidad = "Adoptas un tono guía, equilibrado y cercano enfocado en el aprendizaje autónomo."

    prompt_sistema = f"""Eres un tutor socrático universitario especializado en el modelo de Aprendizaje Autorregulado (SRL).
Fase actual del estudiante: {fase}

ESTILO Y PERSONALIDAD:
{personalidad}

REGLAS SOCRÁTICAS OBLIGATORIAS:
1. Nunca entregues soluciones directas de ejercicios, tareas, exámenes o código completo.
2. Basa tus observaciones en los datos reales del estudiante obtenidos mediante las herramientas (si fueron consultadas), mencionando los nombres de sus actividades cuando corresponda.
3. Cierra siempre con al menos una pregunta reflexiva concreta que invite al estudiante a planificar, monitorear o evaluar su propio aprendizaje.
"""

    mensajes_llm = [SystemMessage(content=prompt_sistema)] + historial
    respuesta = llm.invoke(mensajes_llm)
    
    return {"messages": [respuesta]}

def llm_judge_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluador de calidad pedagógica (LLM-as-a-Judge):
    Verifica que la respuesta generada cumpla estrictamente con el Muro Socrático.
    """
    mensajes = state.get("messages", [])
    if not mensajes:
        return {}
        
    mensaje_borrador = mensajes[-1]
    contenido_borrador = getattr(mensaje_borrador, "content", "")
    fase = state.get("fase_srl_actual", "indefinida")
    
    prompt_juez = f"""Eres un evaluador pedagógico experto (LLM Judge) para un sistema de tutoría socrática universitaria.
Tu tarea es auditar la respuesta propuesta por el tutor antes de enviarla al estudiante.

Fase SRL objetivo: {fase}
Respuesta propuesta por el tutor:
\"\"\"{contenido_borrador}\"\"\"

CRITERIOS DE AUDITORÍA:
1. Muro Socrático: ¿El tutor evitó dar la solución directa, resolución de ejercicios o código final?
2. Pregunta Reflexiva: ¿Incluye al menos una pregunta que fomente la reflexión, monitoreo o planificación del estudiante?
3. Tono Pedagógico: ¿El tono es constructivo y acorde a la fase {fase}?

INSTRUCCIONES:
- Si el mensaje CUMPLE con los criterios socráticos, responde únicamente:
APROBADO
- Si el mensaje VIOLA el muro socrático, responde con la corrección en este formato exacto:
CORREGIDO: [Escribe aquí la versión corregida respetando el método socrático y la fase SRL]"""

    evaluacion = llm.invoke([SystemMessage(content=prompt_juez)])
    texto_eval = evaluacion.content.strip()
    
    if texto_eval.upper().startswith("CORREGIDO:"):
        nuevo_contenido = texto_eval.split(":", 1)[1].strip()
        mensaje_corregido = AIMessage(
            content=nuevo_contenido,
            id=getattr(mensaje_borrador, "id", None)
        )
        return {
            "messages": [mensaje_corregido],
            "evaluacion_juez": {"estado": "corregido", "original": contenido_borrador}
        }
    
    return {
        "evaluacion_juez": {"estado": "aprobado"}
    }