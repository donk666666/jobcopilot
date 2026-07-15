from langgraph.graph import StateGraph, END
from app.agent import AgentState
from app.agent.nodes import (
    rewrite_query,
    retrieve,
    judge_relevance,
    generate,
)


def _route_by_relevance(state: AgentState) -> str:
    answer = state.get("final_answer", "")
    if answer and answer.startswith("抱歉"):
        return END
    return "generate"


def get_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("judge_relevance", judge_relevance)
    graph.add_node("generate", generate)

    graph.set_entry_point("rewrite_query")

    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "judge_relevance")

    graph.add_conditional_edges("judge_relevance", _route_by_relevance, {
        "generate": "generate",
        END: END,
    })

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
