from langgraph.graph import StateGraph, END
from app.agent import AgentState
from app.agent.nodes import (
    retrieve,
    generate,
)


def get_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


def run_agent(message: str, history: list[dict] | None = None) -> dict:
    graph = get_agent_graph()
    state: AgentState = {
        "messages": (history or []) + [{"role": "user", "content": message}],
        "intent": "",
        "rewritten_query": "",
        "retrieved_docs": [],
        "final_answer": "",
    }
    result = graph.invoke(state)
    return {
        "answer": result.get("final_answer", ""),
        "sources": [
            {"source": d["source"], "score": round(d["score"], 3)}
            for d in result.get("retrieved_docs", [])
        ],
    }
