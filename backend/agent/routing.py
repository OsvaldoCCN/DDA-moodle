from typing import Literal

def route_tools(state) -> Literal["tools", "__end__"]:
    """Enruta a las herramientas si el LLM decidió usarlas, o termina el ciclo."""
    last_message = state["messages"][-1]
    
    # Si el LLM incluyó llamadas a herramientas (tool_calls), vamos al nodo 'tools'
    if last_message.tool_calls:
        return "tools"
    
    # Si no, el grafo termina y le muestra el mensaje al usuario
    return "__end__"