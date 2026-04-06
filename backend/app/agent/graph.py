from langgraph.graph import StateGraph
from app.agent.state import AgentState
from app.agent.nodes import extract_node, retrieve_node, plan_node, generate_node, create_proposal_node, evaluate_node


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("extract", extract_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("plan_proposal", plan_node)  # renamed to avoid conflict with state key 'plan'
    graph.add_node("generate", generate_node)
    graph.add_node("create_proposal", create_proposal_node)
    graph.add_node("evaluate", evaluate_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "retrieve")
    graph.add_edge("retrieve", "plan_proposal")
    graph.add_edge("plan_proposal", "generate")
    graph.add_edge("generate", "create_proposal")
    graph.add_edge("create_proposal", "evaluate")

    return graph.compile()