"""记忆压缩模块：滑动窗口 + LLM 摘要 + 上下文构建"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings

# 压缩参数
WINDOW_ROUNDS = 10          # 活跃窗口：最近 N 轮（每轮 = user + assistant 共 2 条）
MAX_SUMMARY_CHARS = 300     # 摘要最大字数
MAX_CONTEXT_TOKENS = 6000   # 上下文 token 上限（估算）


def _create_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约 1 字=1 token，英文约 4 字符=1 token）"""
    return len(text)


def compress_history(messages: list[dict], existing_summary: str = "") -> str:
    """
    将超出窗口的消息压缩为摘要。
    采用增量策略：已有摘要 + 新增超出部分 → 新摘要。

    Args:
        messages: 完整消息列表 [{"role": "user"/"assistant", "content": "..."}, ...]
        existing_summary: 已有的历史摘要

    Returns:
        新的摘要文本（≤ MAX_SUMMARY_CHARS 字）
    """
    window_size = WINDOW_ROUNDS * 2
    if len(messages) <= window_size:
        return existing_summary

    # 只取超出窗口的部分
    overflow = messages[:-window_size]

    # 构建压缩 prompt
    conv_text = "\n".join(
        f"{m['role']}: {m['content'][:200]}"
        for m in overflow[-20:]  # 最多取最近 20 条溢出消息做增量
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

    # 确保不超过字数限制
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS]

    return summary


def build_context(session_id: str, session_store, messages: list[dict]) -> tuple[list[dict], str]:
    """
    构建传给 Agent 的最终上下文。

    Args:
        session_id: 会话 ID
        session_store: SessionStore 实例
        messages: 当前会话完整消息列表

    Returns:
        (context_messages, summary) 元组
            - context_messages: 传给 Agent 的消息列表 [{"role":..., "content":...}, ...]
            - summary: 生成的摘要（供外部写入 DB）
    """
    window_size = WINDOW_ROUNDS * 2
    summary = session_store.get_summary(session_id) or ""

    # 是否需要压缩
    if len(messages) > window_size:
        last_compressed_idx = session_store.get_summary_last_idx(session_id)
        overflow = messages[:-window_size]

        # 检查是否有新的溢出消息需要增量压缩
        new_overflow = [m for m in overflow if m.get("id", 0) > last_compressed_idx]
        if new_overflow:
            summary = compress_history(messages, existing_summary=summary)
            session_store.save_summary(session_id, summary, messages[-window_size - 1].get("id", 0) if messages else 0)

    # 窗口消息
    window_msgs = messages[-window_size:] if len(messages) > window_size else messages

    # 构建最终上下文
    context_messages = []
    if summary:
        context_messages.append({"role": "system", "content": f"[对话历史摘要]\n{summary}"})

    context_messages.extend(
        {"role": m["role"], "content": m["content"]}
        for m in window_msgs
    )

    # token 上限兜底：缩减窗口
    total_text = "".join(m["content"] for m in context_messages)
    if _estimate_tokens(total_text) > MAX_CONTEXT_TOKENS:
        # 缩减到 5 轮
        reduced = window_msgs[-10:] if len(window_msgs) > 10 else window_msgs
        context_messages = []
        if summary:
            # 压缩摘要为更短版本
            short_summary = summary[:150]
            context_messages.append({"role": "system", "content": f"[历史摘要]\n{short_summary}"})
        context_messages.extend(
            {"role": m["role"], "content": m["content"]}
            for m in reduced
        )

    return context_messages, summary
