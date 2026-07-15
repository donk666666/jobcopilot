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
    """判断用户意图：是技术问题还是非技术闲聊"""
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
    """将上下文相关的问题改写为独立检索语句"""
    user_msg = _get_last_user_message(state)

    # 收集最近几轮对话作为上下文
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
    """执行混合检索"""
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = hybrid_search(query, top_k=5)
    return {"retrieved_docs": docs}


def judge_relevance(state: AgentState) -> dict:
    """判断检索结果与问题的相关性"""
    query = state.get("rewritten_query") or _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    if not docs:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中未找到相关内容。"}

    # 最高分高于阈值则视为相关
    max_score = docs[0]["score"]
    is_relevant = max_score >= 0.3

    if not is_relevant:
        return {"need_clarify": False, "final_answer": "抱歉，知识库中暂无与您问题相关的文档。请尝试换个方式提问，或上传相关文档后再试。"}

    return {"need_clarify": False, "final_answer": ""}


def generate(state: AgentState) -> dict:
    """基于检索结果生成回答（合并对话上下文，无需独立改写节点）"""
    user_msg = _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    # 收集最近几轮对话作为上下文
    recent_msgs = state["messages"][-6:]
    history_ctx = "\n".join(
        f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}"
        for m in recent_msgs if isinstance(m, dict)
    )

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

文档片段：
{contexts}

对话历史：
{history_ctx}""")

    recent = [m for m in state["messages"] if isinstance(m, dict)][-4:]
    resp = llm.invoke(
        [system]
        + [HumanMessage(content=m["content"]) if m["role"] == "user" else SystemMessage(content=m["content"]) for m in recent]
        + [HumanMessage(content=user_msg)]
    )

    return {"final_answer": resp.content, "rewritten_query": user_msg}


def clarify(state: AgentState) -> dict:
    """判断回答是否够清晰，是否需要反问"""
    answer = state.get("final_answer", "")
    query = state.get("rewritten_query") or _get_last_user_message(state)

    if not answer or answer.startswith("抱歉"):
        return {"need_clarify": False}

    # 回答过短可能不够清晰，但不强制追问
    if len(answer) < 60:
        prompt = f"问题：{query}\n回答：{answer}\n这个回答是否信息不足、需要追问？只回复 true 或 false"
        llm = create_llm(temperature=0.0)
        resp = llm.invoke([HumanMessage(content=prompt)])
        return {"need_clarify": "true" in resp.content.lower()}

    return {"need_clarify": False}
