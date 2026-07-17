# LangGraph 核心概念

## StateGraph — 状态图

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    messages: list[dict]
    intent: str
    retrieved_docs: list[dict]
    final_answer: str

graph = StateGraph(AgentState)
```

StateGraph 是整个工作流的骨架，所有节点共享同一个 TypedDict 状态对象，节点之间通过修改状态字段来传递数据。

## 节点 — add_node

```python
def retrieve(state: AgentState) -> dict:
    """从向量库检索相关文档"""
    query = state["messages"][-1]["content"]
    docs = hybrid_search(query, top_k=5)
    return {"retrieved_docs": docs}

def generate(state: AgentState) -> dict:
    """基于检索结果调用 LLM 生成回答"""
    docs = state["retrieved_docs"]
    context = "\n".join(d["content"] for d in docs[:2])
    prompt = f"根据以下文档回答：\n{context}"
    answer = llm.invoke(prompt)
    return {"final_answer": answer}

graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)
```

每个节点是一个纯函数，输入是整个 State，返回一个 dict（仅包含要更新的字段），框架自动做状态合并。

## 边 — add_edge

```python
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)
```

边分三种：
- 普通边 `add_edge("A", "B")`：A 执行完必定进入 B
- 条件边 `add_conditional_edges("A", router, {"path1": "B", "path2": "C"})`：根据 router 返回值动态选择下一节点
- 入口 `set_entry_point("A")`：工作流从 A 开始

## 条件分支

```python
def judge_relevance(state: AgentState) -> str:
    docs = state.get("retrieved_docs", [])
    if not docs or docs[0]["score"] < 0.45:
        return "reject"
    return "generate"

graph.add_conditional_edges(
    "retrieve",
    judge_relevance,
    {
        "reject": "fallback",
        "generate": "generate",
    }
)

def fallback(state: AgentState) -> dict:
    return {"final_answer": "抱歉，知识库中未找到相关内容。"}

graph.add_node("fallback", fallback)
graph.add_edge("fallback", END)
```

条件边让图有了"决策"能力——根据检索质量决定是继续生成还是直接降级回复。

## 编译与调用

```python
app = graph.compile()
result = app.invoke({
    "messages": [{"role": "user", "content": "FastAPI 怎么处理文件上传？"}],
    "intent": "",
    "retrieved_docs": [],
    "final_answer": "",
})
print(result["final_answer"])
```

`compile()` 将图编译为可执行的 Runnable，`invoke()` 传入初始状态并返回最终状态。

## Checkpoint — 对话记忆

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
app = graph.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "user_123"}}
app.invoke(state, config)  # 第一次调用
app.invoke(state, config)  # 自动加载上一轮的对话状态
```

每次 `invoke` 后状态自动持久化到 checkpointer，下次同一 `thread_id` 调用时自动恢复上下文。

## 与 Chain 的区别

| 维度 | LangGraph | Chain (LCEL) |
|------|-----------|--------------|
| 结构 | 有向图，可循环 | 线性管道，单向 |
| 分支 | 条件边动态路由 | 无原生分支 |
| 状态持久化 | Checkpoint 内置 | 需手动管理 |
| 适用场景 | 多步 Agent、RAG+判断 | 单步 LLM 调用 |

## Subgraph — 嵌套子图

```python
parent = StateGraph(ParentState)
child = StateGraph(ChildState)

# 子图定义...
compiled_child = child.compile()

parent.add_node("child_step", compiled_child)
parent.add_edge("start", "child_step")
parent.add_edge("child_step", END)
```

复杂流程可以拆分为多个子图，父图将子图当作一个普通节点调用，输入/输出通过状态字段映射。
