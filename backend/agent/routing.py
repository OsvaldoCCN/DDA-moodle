from typing import Literal

def route_tools(state) -> Literal["tools", "__end__"]:
    """Enruta a las herramientas si el LLM decidió usarlas, o termina el ciclo."""
    last_message = state["messages"][-1]
    

    if last_message.tool_calls:
        return "tools"
    

    return "__end__"