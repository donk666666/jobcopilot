"""记忆压缩模块：滑动窗口 + LLM 摘要 + 上下文构建"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings

WINDOW_ROUNDS = 10
MAX_SUMMARY_CHARS = 300
MAX_CONTEXT_TOKENS = 6000


def _create_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )


def _estimate_tokens(text: str) -> int:
    return len(text)


def compress_history(messages: list[dict], existing_summary: str = "") -> str:
    window_size = WINDOW_ROUNDS * 2
    if len(messages) <= window_size:
        return existing_summary

    overflow = messages[:-window_size]

    conv_text = "\n".join(
        f"{m['role']}: {m['content'][:200]}"
        for m in overflow[-20:]
    )

    llm = _create_llm(temperature=0.1)
    system = SystemMessage(content=f"""你是一个对话摘要器。请将以下对话片段压缩为一段简洁的摘要。

规则：
- 摘要不超过 {MAX_SUMMARY_CHARS} 字
- 包含：关键话题、重要结论、待办事项
- 如果已有历史摘要，将其与新内容合并，避免信息丢失
- 用中文输出，只输出摘要文本，不要加额外说明
- 如果对话内容很少或无关紧要，输出空字符串

{"已有历史摘要：" + existing_summary if existing_summary else ""}""")

    resp = llm.invoke([system, HumanMessage(content=conv_text)])
    summary = resp.content.strip().strip('"').strip("'")

    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS]

    return summary


def build_context(
    session_id: str, user_id: str, session_store, messages: list[dict]
) -> tuple[list[dict], str]:
    window_size = WINDOW_ROUNDS * 2
    summary = session_store.get_summary(session_id, user_id) or ""

    if len(messages) > window_size:
        last_compressed_idx = session_store.get_summary_last_idx(session_id, user_id)
        overflow = messages[:-window_size]

        new_overflow = [m for m in overflow if m.get("id", 0) > last_compressed_idx]
        if new_overflow:
            summary = compress_history(messages, existing_summary=summary)
            last_idx = messages[-window_size - 1].get("id", 0) if len(messages) > window_size else 0
            session_store.save_summary(session_id, user_id, summary, last_idx)

    window_msgs = messages[-window_size:] if len(messages) > window_size else messages

    context_messages = []
    if summary:
        context_messages.append({"role": "system", "content": f"[对话历史摘要]\n{summary}"})

    context_messages.extend(
        {"role": m["role"], "content": m["content"]}
        for m in window_msgs
    )

    total_text = "".join(m["content"] for m in context_messages)
    if _estimate_tokens(total_text) > MAX_CONTEXT_TOKENS:
        reduced = window_msgs[-10:] if len(window_msgs) > 10 else window_msgs
        context_messages = []
        if summary:
            context_messages.append({"role": "system", "content": f"[历史摘要]\n{summary[:150]}"})
        context_messages.extend(
            {"role": m["role"], "content": m["content"]}
            for m in reduced
        )

    return context_messages, summary
