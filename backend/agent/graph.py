from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import (
    gatekeeper_node, 
    srl_classifier_node, 
    data_orchestrator_node, 
    tool_node,
    generator_node, 
    llm_judge_node
)
from routing import route_gatekeeper, route_orchestrator

# Inicialización del Grafo de Estado
workflow = StateGraph(AgentState)

# Registro de Nodos
workflow.add_node("gatekeeper", gatekeeper_node)
workflow.add_node("srl_classifier", srl_classifier_node)
workflow.add_node("data_orchestrator", data_orchestrator_node)
workflow.add_node("tools", tool_node)
workflow.add_node("generator", generator_node)
workflow.add_node("llm_judge", llm_judge_node)

# Flujo de Ejecución y Aristas Condicionales
workflow.set_entry_point("gatekeeper")

# Si el gatekeeper rechaza la consulta, corta a END. Si es válida, clasifica SRL.
workflow.add_conditional_edges(
    "gatekeeper",
    route_gatekeeper,
    {
        "srl_classifier": "srl_classifier",
        "__end__": END
    }
)

workflow.add_edge("srl_classifier", "data_orchestrator")

# Si el orquestador solicita herramientas, va a 'tools'; si no, directo a 'generator'
workflow.add_conditional_edges(
    "data_orchestrator",
    route_orchestrator,
    {
        "tools": "tools",
        "generator": "generator"
    }
)

# Tras ejecutar herramientas, se pasa al generador para producir la respuesta socrática
workflow.add_edge("tools", "generator")

# Del generador pasa al evaluador de calidad pedagógica (LLM Judge)
workflow.add_edge("generator", "llm_judge")

# El juez valida y finaliza el ciclo
workflow.add_edge("llm_judge", END)

app = workflow.compile()