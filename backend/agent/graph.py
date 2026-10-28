from langgraph.graph import StateGraph, START, END
from state import AgentState
from nodes import call_model, tool_node
from routing import route_tools


workflow = StateGraph(AgentState)


workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)


workflow.add_edge(START, "agent")


workflow.add_conditional_edges(
    "agent",
    route_tools,
    {"tools": "tools", "__end__": END}
)


workflow.add_edge("tools", "agent")


app = workflow.compile()