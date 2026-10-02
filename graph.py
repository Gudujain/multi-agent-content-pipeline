from langgraph.graph import StateGraph, START, END
from state import PipelineState
from nodes import researcher, writer, editor, route_after_editor


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("researcher", researcher)
    g.add_node("writer", writer)
    g.add_node("editor", editor)

    g.add_edge(START, "researcher")
    g.add_edge("researcher", "writer")
    g.add_edge("writer", "editor")
    g.add_conditional_edges(
        "editor",
        route_after_editor,
        {"revise": "writer", "end": END},
    )
    return g.compile()