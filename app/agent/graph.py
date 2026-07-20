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


def run_agent(message: str, context: list[dict] | None = None) -> dict:
    """
    运行 Agent。

    Args:
        message: 当前用户消息
        context: 已构建好的上下文消息列表，结构为：
                 [system(含历史摘要)] + [窗口消息(role+content)] + ...
                 调用方（main.py / memory 模块）负责组装。
    """
    graph = get_agent_graph()

    if context is None:
        context = []

    state: AgentState = {
        "messages": context + [{"role": "user", "content": message}],
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
