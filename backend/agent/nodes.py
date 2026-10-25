from langchain_core.messages import SystemMessage
from llm import llm, SYSTEM_PROMPT
from tools import tools
from langgraph.prebuilt import ToolNode

# Nodo 1: Ejecutor de Herramientas (Ya viene prefabricado en LangGraph)
tool_node = ToolNode(tools)

# Nodo 2: El Cerebro (Llama al LLM)
def call_model(state):
    messages = state["messages"]
    estudiante_id = state.get("estudiante_id", 1) # Por defecto 1 si no se envía
    
    # Inyectamos el prompt base + el ID del alumno activo sin que este lo note
    mensaje_sistema = f"{SYSTEM_PROMPT}\n\n[CONTEXTO OCULTO: El ID local del alumno con el que hablas es {estudiante_id}. Usa este ID para tus herramientas.]"
    sys_msg = SystemMessage(content=mensaje_sistema)
    
    # Vinculamos las herramientas al LLM para que sepa que existen
    llm_with_tools = llm.bind_tools(tools)
    
    # El LLM genera la respuesta (o decide llamar a una tool)
    response = llm_with_tools.invoke([sys_msg] + messages)
    
    return {"messages": [response]}