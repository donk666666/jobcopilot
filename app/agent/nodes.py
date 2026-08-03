import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
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
    context 已由 memory.build_context 预处理。
    """
    user_msg = _get_last_user_message(state)
    docs = state.get("retrieved_docs", [])

    # 动态选文档：分数 >= 0.5 的优先，至少 1 篇，最多 5 篇
    qualified = [d for d in docs if d["score"] >= 0.5]
    selected = (qualified or docs[:1])[:5]

    contexts = "\n---\n".join(
        f"[来源: {d['source']} (相关度: {d['score']:.2f})]\n{d['content']}"
        for d in selected
    )

    # 非技术问题时用更宽松的 prompt
    is_tech = state.get("intent") == "tech"
    if is_tech or docs:
        system_prompt = f"""你是智能文档助手，一个帮助用户查询技术文档的 AI 助手。如果用户询问你的身份或名字，回答你是"智能文档助手"。你根据以下检索到的文档片段回答用户问题。

规则：
- 只回答用户最新的问题，不要重复或整合对话历史中已出现过的话题和内容
- 每个回答独立、干净，历史对话仅用于理解上下文（如代词指代），不用于拼凑答案
- 回答基于文档内容，不要编造信息
- 如果文档信息不足以完整回答，诚实说明
- 当回答涉及对比、参数、规格、步骤、适用场景等多维信息时，优先使用 markdown 表格组织内容，表格需有清晰的列名
- 回答末尾引用来源文件名
- 使用中文回答

文档片段：
{contexts}"""
    else:
        system_prompt = """你是智能文档助手，一个友好的 AI 助手。用简洁自然的中文回答用户的问题。"""

    llm = create_llm(temperature=0.5)
    system = SystemMessage(content=system_prompt)

    all_msgs = [m for m in state["messages"] if isinstance(m, dict)]
    if all_msgs and all_msgs[-1]["role"] == "user":
        all_msgs = all_msgs[:-1]
    chat_msgs = []
    for m in all_msgs:
        if m["role"] == "system":
            chat_msgs.append(SystemMessage(content=m["content"]))
        elif m["role"] == "assistant":
            chat_msgs.append(AIMessage(content=m["content"]))
        else:
            chat_msgs.append(HumanMessage(content=m["content"]))

    resp = llm.invoke([system] + chat_msgs + [HumanMessage(content=user_msg)])
    answer = resp.content

    # 验证：确保回答引用了至少一个来源
    if selected:
        mentioned = any(d["source"].replace(".md", "").replace(".txt", "") in answer for d in selected)
        if not mentioned:
            answer += "\n\n> 参考来源：" + "、".join(d["source"] for d in selected)

    return {"final_answer": answer, "rewritten_query": user_msg}


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
