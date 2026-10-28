from typing import TypedDict, Dict, Any, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_message: str
    
    estudiante_id: int
    curso_id: Optional[int]
    
    es_valido: bool
    fase_srl_actual: str
    contexto_academico: Dict[str, Any]
    tipo_interaccion: str
    evaluacion_juez: Dict[str, Any]