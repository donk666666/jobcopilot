from langgraph.graph import StateGraph, END
from app.agent import AgentState
from app.agent.nodes import (
    classify_intent,
    rewrite_query,
    retrieve,
    judge_relevance,
    generate,
    clarify,
)


def _route_by_intent(state: AgentState) -> str:
    if state.get("intent") == "tech":
        return "rewrite_query"
    return "fallback"


def _route_by_relevance(state: AgentState) -> str:
    answer = state.get("final_answer", "")
    if answer and answer.startswith("抱歉"):
        return "fallback"
    return "generate"


def _route_by_clarity(state: AgentState) -> str:
    if state.get("need_clarify"):
        return "rephrase"
    return END


def _fallback_node(state: AgentState) -> dict:
    answer = state.get("final_answer") or "请提出技术相关问题，我会基于知识库为您解答。"
    return {"final_answer": answer, "need_clarify": False}


def _rephrase_node(state: AgentState) -> dict:
    answer = state.get("final_answer", "")
    return {"final_answer": f"{answer}\n\n如果您的问题还未解决，可以尝试更具体地描述，或者换个问法。"}


def get_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("judge_relevance", judge_relevance)
    graph.add_node("generate", generate)
    graph.add_node("clarify", clarify)
    graph.add_node("fallback", _fallback_node)
    graph.add_node("rephrase", _rephrase_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges("classify_intent", _route_by_intent, {
        "rewrite_query": "rewrite_query",
        "fallback": "fallback",
    })

    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "judge_relevance")

    graph.add_conditional_edges("judge_relevance", _route_by_relevance, {
        "generate": "generate",
        "fallback": "fallback",
    })

    graph.add_edge("generate", "clarify")

    graph.add_conditional_edges("clarify", _route_by_clarity, {
        "rephrase": "rephrase",
        END: END,
    })

    graph.add_edge("fallback", END)
    graph.add_edge("rephrase", END)

    return graph.compile()


def run_agent(message: str, history: list[dict] | None = None) -> dict:
    graph = get_agent_graph()
    state: AgentState = {
        "messages": (history or []) + [{"role": "user", "content": message}],
        "intent": "",
        "rewritten_query": "",
        "retrieved_docs": [],
        "final_answer": "",
        "need_clarify": False,
    }
    result = graph.invoke(state)
    return {
        "answer": result.get("final_answer", ""),
        "sources": [
            {"source": d["source"], "score": round(d["score"], 3)}
            for d in result.get("retrieved_docs", [])
        ],
    }
