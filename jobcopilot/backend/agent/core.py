"""
LangChain ReAct Agent 核心引擎

实现 ReAct 模式：Thought → Action → Observation → ... → Final Answer

参考了 how-claude-code-works 中的 Agent Loop 设计理念：
1. 上下文组装 → 模型决策 → 工具执行 → 结果注入 → 继续/停止
"""

import json
import re
from typing import Optional, AsyncIterator, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from agent.tools import get_all_tools
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


def _extract_json(text: str):
    """健壮地从 LLM 输出中提取 JSON：支持代码块/纯JSON/带杂文"""
    if not text:
        return None
    # 1) 代码块内 JSON
    m = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2) 从第一个 { 开始做括号配对，提取最外层完整 JSON
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
    # 3) 整体解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ReAct 提示词模板
REACT_PROMPT = PromptTemplate.from_template("""你是一个AI求职助手，名叫 JobCopilot。你可以使用以下工具来帮助求职者：

{tools}

工具名称：{tool_names}

请使用以下格式回答：

Question: 用户的问题
Thought: 我应该思考如何处理这个问题
Action: 要使用的工具名称（必须是 [{tool_names}] 之一）
Action Input: 工具的输入参数（JSON格式）
Observation: 工具执行的结果
... (这个 Thought/Action/Action Input/Observation 可以重复多次)
Thought: 我现在知道最终答案了
Final Answer: 给用户的有用回答

## 规则
1. 一次只使用一个工具
2. Action Input 必须是有效的JSON格式
3. 当用户想分析JD时，使用 analyze_jd 工具
4. 当用户想匹配简历时，使用 match_resume 工具
5. 当用户想优化简历时，使用 tailor_resume 工具
6. 当用户想生成求职信时，使用 generate_cover_letter 工具
7. 如果你无法使用工具完成任务，请诚实告知用户

开始!

Question: {input}
Thought: {agent_scratchpad}""")


class JobCopilotAgent:
    """
    JobCopilot AI Agent 核心类

    封装了 LangChain ReAct Agent 的完整生命周期：
    初始化 → 工具注册 → Agent创建 → 执行 → 流式输出
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://cloud.hongqiye.com/v1",
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        verbose: bool = False
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.verbose = verbose

        # 初始化LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            streaming=True,
        )

        # 初始化工具
        self.tools = get_all_tools()

        # 创建 ReAct Agent（langgraph 版，工具自动注入）
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_modifier=REACT_PROMPT.template,
        )

    async def run(self, question: str) -> Dict[str, Any]:
        """
        运行Agent处理用户问题

        返回格式：
        {
            "output": "最终回答",
            "success": True/False,
            "error": "错误信息(如有)"
        }
        """
        try:
            result = await self.agent.ainvoke({"messages": [HumanMessage(content=question)]})
            msgs = result.get("messages", [])
            output = msgs[-1].content if msgs else ""
            return {
                "output": output,
                "success": True
            }
        except Exception as e:
            return {
                "output": f"执行出错：{str(e)}",
                "success": False,
                "error": str(e)
            }

    async def run_stream(self, question: str) -> AsyncIterator[str]:
        """流式运行Agent，实时返回结果"""
        async for event in self.agent.astream({"messages": [HumanMessage(content=question)]}):
            if "messages" in event:
                msg = event["messages"][-1]
                content = getattr(msg, "content", "")
                if content and not isinstance(msg, (HumanMessage, SystemMessage)):
                    yield content


# ============================================================
# 直接调用函数（绕过Agent，用于API端点直接调用）
# 这些函数封装了常见的单步操作，提供更快的响应
# ============================================================

async def analyze_jd_direct(jd_text: str, api_key: str, base_url: str) -> Dict[str, Any]:
    """直接调用LLM分析JD（不走Agent，更快）"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=DEEPSEEK_MODEL,
        temperature=0.3,
        max_tokens=400,
    )

    messages = [
        SystemMessage(content=JD_ANALYZER_SYSTEM),
        HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd_text))
    ]

    response = await llm.ainvoke(messages)
    content = response.content

    # 尝试提取JSON
    try:
        # 处理可能包含的markdown代码块
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        parsed = json.loads(content)
        # 归一化 experience_years：如果是对象取平均值
        if isinstance(parsed.get("experience_years"), dict):
            exp = parsed["experience_years"]
            avg = (exp.get("min", 0) + exp.get("max", 0)) / 2
            parsed["experience_years"] = avg
        return {"result": parsed, "raw": response.content, "success": True}
    except json.JSONDecodeError:
        return {"result": None, "raw": response.content, "success": False, "error": "JSON解析失败"}


async def match_resume_direct(
    jd_analysis: str, resume_text: str, api_key: str, base_url: str
) -> Dict[str, Any]:
    """直接调用LLM进行简历匹配（不走Agent）"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.resume_tailor import RESUME_MATCH_SYSTEM, RESUME_MATCH_USER_TEMPLATE
    from rag.vector_store import get_vector_store

    # RAG检索
    vector_store = get_vector_store()
    vector_store.add_resume(resume_text)
    rag_context = vector_store.search_all(resume_text, top_k=5)

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=DEEPSEEK_MODEL,
        temperature=0.5,
    )

    messages = [
        SystemMessage(content=RESUME_MATCH_SYSTEM),
        HumanMessage(content=RESUME_MATCH_USER_TEMPLATE.format(
            jd_analysis=jd_analysis,
            resume_text=resume_text,
            rag_context=rag_context
        ))
    ]

    response = await llm.ainvoke(messages)
    content = response.content

    parsed = _extract_json(content)
    if parsed is None:
        # 解析失败重试一次（降 temperature 提高稳定性）
        llm.temperature = 0.2
        try:
            response = await llm.ainvoke(messages)
            parsed = _extract_json(response.content)
        except Exception:
            parsed = None
    if parsed is not None:
        return {"result": parsed, "rag_context": rag_context, "success": True}
    return {"result": None, "raw": response.content, "success": False, "error": "JSON解析失败"}


async def tailor_resume_direct(
    jd_analysis: str, match_result: str, resume_text: str, api_key: str, base_url: str
) -> Dict[str, Any]:
    """直接调用LLM改写简历"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.resume_tailor import RESUME_TAILOR_SYSTEM, RESUME_TAILOR_USER_TEMPLATE

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=DEEPSEEK_MODEL,
        temperature=0.6,
    )

    messages = [
        SystemMessage(content=RESUME_TAILOR_SYSTEM),
        HumanMessage(content=RESUME_TAILOR_USER_TEMPLATE.format(
            jd_analysis=jd_analysis,
            match_result=match_result,
            resume_text=resume_text
        ))
    ]

    response = await llm.ainvoke(messages)
    return {"result": response.content, "success": True}


async def generate_cover_letter_direct(
    jd_text: str, resume_text: str, candidate_name: str,
    style: str, recipient: str, api_key: str, base_url: str
) -> Dict[str, Any]:
    """直接调用LLM生成求职信（链式Prompt）"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from prompts.cover_letter import (
        COMPANY_ANALYSIS_SYSTEM, COMPANY_ANALYSIS_TEMPLATE,
        EXPERIENCE_MATCH_SYSTEM, EXPERIENCE_MATCH_TEMPLATE,
        COVER_LETTER_SYSTEM, COVER_LETTER_TEMPLATE, STYLE_OPTIONS
    )
    from rag.vector_store import get_vector_store

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=DEEPSEEK_MODEL,
        temperature=0.7,
    )

    # RAG检索
    vector_store = get_vector_store()
    vector_store.add_resume(resume_text)
    rag_context = vector_store.search_all(resume_text, top_k=3)

    style_name = STYLE_OPTIONS.get(style, "正式商务")

    # 构建完整的Chain-of-Thought prompt
    full_prompt = f"""请按以下三个步骤生成一封{style_name}风格的求职信：

## 步骤1：分析公司需求
从以下JD中提取公司核心需求和理想候选人画像：
{jd_text}

## 步骤2：匹配个人经历
从以下简历中找到最能打动面试官的3个核心卖点：
候选人：{candidate_name}
简历：{resume_text}
补充信息（RAG检索）：{rag_context}

## 步骤3：生成求职信
收信人：{recipient}
风格：{style_name}

请直接输出最终的求职信正文。"""

    messages = [
        SystemMessage(content=COVER_LETTER_SYSTEM),
        HumanMessage(content=full_prompt)
    ]

    response = await llm.ainvoke(messages)
    return {"result": response.content, "style": style_name, "success": True}


async def generate_greeting_direct(
    resume_text: str, jd_text: str, company_name: str,
    position_title: str, candidate_name: str, style: str,
    variant_count: int, api_key: str, base_url: str
) -> Dict[str, Any]:
    """生成个性化打招呼文案（多变体），用于 Boss直聘/脉脉等私信场景"""
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=DEEPSEEK_MODEL,
        temperature=0.8,
    )

    style_guide = {
        "casual": "亲和自然：语气真诚自然，有亲和力，像真人打招呼，适合互联网/创业公司",
        "professional": "专业得体：措辞正式但不生硬，突出专业能力和诚意，适合中大型企业",
        "tech": "技术直击：开门见山展示技术栈和项目亮点，简洁有数据，适合技术岗",
    }.get(style, "亲和自然")

    system = """你是一位资深招聘沟通顾问，擅长帮求职者写出一眼打动 HR 的打招呼私信（Boss直聘/脉脉/领英场景）。
打招呼文案要求：
1. 简短有力，80-150字，第一句就要抓住注意力，不要寒暄客套
2. 结合目标JD的关键要求和候选人简历的真实经历，体现针对性，拒绝模板化
3. 突出1-2个与职位最匹配的核心卖点（技能/项目/数据）
4. 结尾自然表达沟通意愿
5. 不要用"尊敬的""您好，我是"等过于正式的求职信开场，要像真实的私信对话"""

    prompt = f"""请根据以下信息，生成 {variant_count} 条不同风格的个性化打招呼文案（用中文）：

## 目标公司
{company_name or '未知公司'}

## 目标职位
{position_title or '未知职位'}

## 职位描述（JD）
{jd_text or '无'}

## 候选人简历
{resume_text}

## 候选人称呼
{candidate_name}

## 语气风格
{style_guide}

## 输出要求
直接输出 {variant_count} 条打招呼文案，每条一行，不要编号，不要额外说明，不要输出 JSON。"""

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt)
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        variants = [v.strip() for v in content.split("\n") if v.strip()]
        return {"variants": variants, "style": style, "success": True}
    except Exception as e:
        return {"variants": [], "success": False, "error": str(e)}

