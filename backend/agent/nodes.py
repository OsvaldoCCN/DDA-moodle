from langchain_core.messages import SystemMessage
from llm import llm, SYSTEM_PROMPT
from tools import tools
from langgraph.prebuilt import ToolNode


tool_node = ToolNode(tools)


def call_model(state):
    messages = state["messages"]
    estudiante_id = state.get("estudiante_id", 1) # 1 por defecto - debug
    

    mensaje_sistema = f"{SYSTEM_PROMPT}\n\n[CONTEXTO OCULTO: El ID local del alumno con el que hablas es {estudiante_id}. Usa este ID para tus herramientas.]"
    sys_msg = SystemMessage(content=mensaje_sistema)
    

    llm_with_tools = llm.bind_tools(tools)
    

    response = llm_with_tools.invoke([sys_msg] + messages)
    
    return {"messages": [response]}