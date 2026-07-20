import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.rag.retriever import hybrid_search
from app.agent import AgentState


def create_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )


def _get_last_user_message(state: AgentState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg["content"]
        elif hasattr(msg, "type") and msg.type == "human":
            return msg.content
    return ""


def classify_intent(state: AgentState) -> dict:
    user_msg = _get_last_user_message(state)
    llm = create_llm(temperature=0.0)

    system = SystemMessage(content="""你是一个意图分类器。判断用户消息是否属于技术问题。
技术问题包括：编程、框架、工具、计算机科学、软件开发、DevOps、算法、数据库等。
非技术问题包括：闲聊、天气、新闻、娱乐等。

请只回复 JSON：{"is_tech": true/false}""")

    resp = llm.invoke([system, HumanMessage(content=user_msg)])
    try:
        result = json.loads(resp.content)
    except Exception:
        result = {"is_tech": True}

    return {"intent": "tech" if result.get("is_tech") else "non_tech"}


def rewrite_query(state: AgentState) -> dict:
    user_msg = _get_last_user_message(state)

    recent_msgs = state["messages"][-6:]
    context = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
        for m in recent_msgs if isinstance(m, dict)
    )

    llm = create_llm(temperature=0.1)
    system = SystemMessage(content=f"""你是一个查询改写器。将用户问题结合对话上下文，改写为一个适合向量检索的独立查询语句。
规则：
- 如果问题是追问（如"那怎么用"），请补全它指代的内容
- 保持技术术语的准确性
- 只输出改写后的查询语句，不要加额外说明

对话上下文：
{context}""")

    resp = llm.invoke([system, HumanMessage(content=user_msg)])
    rewritten = resp.content.strip().strip('"').strip("'")
    return {"rewritten_query": rewritten}


def retrieve(state: AgentState) -> dict:
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = hybrid_search(query, top_k=5)
    return {"retrieved_docs": docs}


def judge_relevance(state: AgentState) -> dict:
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中未找到相关内容。"}

    max_score = docs[0]["score"]
    is_relevant = max_score >= 0.3

    if not is_relevant:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中暂无与您问题相关的文档。请尝试换个方式提问，或上传相关文档后再试。"}

    return {"need_clarify": False, "final_answer": ""}


def generate(state: AgentState) -> dict:
    """
    基于检索结果生成回答。
    context 已由 memory.build_context 预处理：
    - system 消息（含历史摘要，如有）
    - 窗口内最近 10 轮完整消息
    - 当前用户消息在末尾
    此处不再重复截取历史，直接使用 state["messages"]。
    """
    user_msg = _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    contexts = "\n---\n".join(
        f"[来源: {d['source']}]\n{d['content']}"
        for d in docs[:2]
    )

    llm = create_llm(temperature=0.5)
    system = SystemMessage(content=f"""你是一个技术文档问答助手。根据以下检索到的文档片段回答用户问题。

规则：
- 回答基于文档内容，不要编造信息
- 如果文档信息不足以完整回答，诚实说明
- 回答末尾引用来源文件名
- 使用中文回答
- 如果对话上下文中包含"历史摘要"，参考它来理解对话背景

文档片段：
{contexts}""")

    # 使用 memory 模块预处理好的上下文消息（已含摘要 + 窗口）
    # 保留所有 system 和最近的用户/助手消息
    all_msgs = [m for m in state["messages"] if isinstance(m, dict)]
    chat_msgs = []
    for m in all_msgs:
        if m["role"] == "system":
            chat_msgs.append(SystemMessage(content=m["content"]))
        elif m["role"] == "assistant":
            chat_msgs.append(SystemMessage(content=m["content"]))
        else:
            chat_msgs.append(HumanMessage(content=m["content"]))
    resp = llm.invoke([system] + chat_msgs + [HumanMessage(content=user_msg)])

    return {"final_answer": resp.content, "rewritten_query": user_msg}


def clarify(state: AgentState) -> dict:
    answer = state.get("final_answer", "")
    query = state.get("rewritten_query") or _get_last_user_message(state)

    if not answer or answer.startswith("抱歉"):
        return {"need_clarify": False}

    if len(answer) < 60:
        prompt = f"问题：{query}\n回答：{answer}\n这个回答是否信息不足、需要追问？只回复 true 或 false"
        llm = create_llm(temperature=0.0)
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"need_clarify": "true" in resp.content.lower()}

    return {"need_clarify": False}
