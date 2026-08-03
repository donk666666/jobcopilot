import asyncio
import json
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

# 节点名 → 用户可见的步骤名
NODE_STEP_NAMES = {
    "classify_intent": "意图分类",
    "rewrite_query": "查询改写",
    "retrieve": "检索知识库",
    "judge_relevance": "相关性判断",
    "generate": "生成回答",
    "clarify": "追问澄清",
}


def _route_after_intent(state: AgentState) -> str:
    """非技术问题跳过检索，直接生成"""
    if state.get("intent") != "tech":
        return "generate"
    return "rewrite_query"


def _route_after_judge(state: AgentState) -> str:
    """不相关时 judge 已设 final_answer 兜底，直接结束"""
    if state.get("final_answer"):
        return END
    return "generate"


def get_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("judge_relevance", judge_relevance)
    graph.add_node("generate", generate)
    graph.add_node("clarify", clarify)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent", _route_after_intent,
        {"rewrite_query": "rewrite_query", "generate": "generate"},
    )
    graph.add_edge("rewrite_query", "retrieve")
    graph.add_edge("retrieve", "judge_relevance")
    graph.add_conditional_edges(
        "judge_relevance", _route_after_judge,
        {"generate": "generate", END: END},
    )
    graph.add_edge("generate", "clarify")
    graph.add_edge("clarify", END)

    return graph.compile()


def _make_state(message: str, context: list[dict] | None) -> AgentState:
    if context is None:
        context = []
    return {
        "messages": context + [{"role": "user", "content": message}],
        "intent": "",
        "rewritten_query": "",
        "retrieved_docs": [],
        "final_answer": "",
        "need_clarify": False,
    }


def run_agent(message: str, context: list[dict] | None = None) -> dict:
    """
    运行 Agent（非流式，兼容旧调用）。
    """
    graph = get_agent_graph()
    result = graph.invoke(_make_state(message, context))
    return {
        "answer": result.get("final_answer", ""),
        "sources": [
            {"source": d["source"], "score": round(d["score"], 3)}
            for d in result.get("retrieved_docs", [])
        ],
    }


async def run_agent_stream(message: str, context: list[dict] | None = None):
    """
    流式运行 Agent，通过 astream 逐节点播报步骤进度。
    """
    graph = get_agent_graph()
    state = _make_state(message, context)
    steps = list(NODE_STEP_NAMES.values())

    # 告诉前端完整的步骤列表
    yield ("__init__", {"event": "init", "steps": steps})

    doc_count = 0
    max_score = 0.0
    final_answer = ""
    sources = []
    actual_steps: list[str] = []

    async for chunk in graph.astream(state):
        for node_name, output in chunk.items():
            step_name = NODE_STEP_NAMES.get(node_name, node_name)
            detail = ""
            status = "done"

            if node_name == "classify_intent":
                intent = output.get("intent", "")
                detail = "技术问题" if intent == "tech" else "非技术问题，直接回答"

            elif node_name == "rewrite_query":
                rewritten = output.get("rewritten_query", "")
                detail = rewritten[:50] if rewritten else ""

            elif node_name == "retrieve":
                docs = output.get("retrieved_docs", [])
                doc_count = len(docs)
                max_score = max((d["score"] for d in docs), default=0)
                detail = f"找到 {doc_count} 篇文档，最高分 {max_score:.2f}"
                sources = [{"source": d["source"], "score": round(d["score"], 3)} for d in docs]

            elif node_name == "judge_relevance":
                if output.get("final_answer"):
                    detail = "未找到相关文档，已给出兜底回答"
                    status = "skip"
                else:
                    detail = f"相关性达标（最高分 {max_score:.2f}）"

            elif node_name == "generate":
                final_answer = output.get("final_answer", "")

            elif node_name == "clarify":
                detail = "信息可能不足，已标记" if output.get("need_clarify") else "信息充分"

            actual_steps.append(step_name)
            yield (node_name, {
                "event": "step",
                "step": step_name,
                "status": status,
                "detail": detail,
                "actualSteps": actual_steps,
            })

    yield ("__done__", {"event": "answer", "answer": final_answer, "sources": sources})
