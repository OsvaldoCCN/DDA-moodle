from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # add_messages asegura que los mensajes nuevos se sumen al historial, no que lo sobrescriban
    messages: Annotated[list, add_messages]
    estudiante_id: int