from typing import Literal

def route_gatekeeper(state: dict) -> Literal["srl_classifier", "__end__"]:
    """
    Si el gatekeeper determinó que la consulta no es válida (intento de trampa),
    termina el grafo inmediatamente entregando el mensaje de rechazo pedagógico.
    Si es válida, continúa hacia el clasificador SRL.
    """
    if state.get("es_valido") is False:
        return "__end__"
        
    messages = state.get("messages", [])
    if messages and getattr(messages[-1], "name", None) == "gatekeeper_rejected":
        return "__end__"
        
    return "srl_classifier"

def route_orchestrator(state: dict) -> Literal["tools", "generator"]:
    """
    Si el orquestador decidió invocar herramientas de base de datos (tool_calls),
    enruta hacia el nodo 'tools'. Si no, pasa directo al generador.
    """
    messages = state.get("messages", [])
    if not messages:
        return "generator"
        
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
        
    return "generator"

def route_tools(state: dict) -> Literal["generator"]:
    """
    Tras ejecutar las herramientas en 'tools', siempre avanza al generador.
    """
    return "generator"