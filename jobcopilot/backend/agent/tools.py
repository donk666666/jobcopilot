"""
LangChain ReAct Agent 工具集 v2.0

每个工具的 _run() 真正执行逻辑：
- LLM 调用（拿到结果）
- RAG 检索（拿到上下文）
- 返回**结构化结果**给 Agent

这样 ReAct Agent 调工具一次 = 拿到一段结果，而不是一段 prompt。
"""

import json
import re
from typing import Type, Optional

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from rag.vector_store import get_vector_store
from prompts.jd_analyzer import JD_ANALYZER_SYSTEM, JD_ANALYZER_USER_TEMPLATE
from prompts.resume_tailor import (
    RESUME_MATCH_SYSTEM, RESUME_MATCH_USER_TEMPLATE,
    RESUME_TAILOR_SYSTEM, RESUME_TAILOR_USER_TEMPLATE
)
from prompts.cover_letter import (
    COMPANY_ANALYSIS_SYSTEM, COMPANY_ANALYSIS_TEMPLATE,
    EXPERIENCE_MATCH_SYSTEM, EXPERIENCE_MATCH_TEMPLATE,
    COVER_LETTER_SYSTEM, COVER_LETTER_TEMPLATE,
)


def _get_llm(api_key: str, base_url: str, model: str, temperature: float = 0.3, max_tokens: int = 2500):
    # reasoning 模型（GLM-5.2 / DeepSeek-R1 等）默认会把 token 全花在思考上，导致 content 为空
    # 通过 extra_body 显式禁用 thinking，保证响应有实质文本
    return ChatOpenAI(
        api_key=api_key, base_url=base_url, model=model,
        temperature=temperature, max_tokens=max_tokens,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _invoke_with_retry(llm, messages, max_attempts: int = 5, sleep_s: float = 1.5):
    """LLM 调用包装：内容为空 / 异常时自动重试（指数退避）

    Returns:
        (content, error) — content 非空表示成功；error 为异常描述
    """
    import time as _t
    last_err = None
    for attempt in range(max_attempts):
        try:
            resp = llm.invoke(messages)
            content = (resp.content or "").strip() if resp.content else ""
            if content:
                return content, None
            # 记录空响应的 finish_reason 便于排查
            try:
                fr = getattr(resp, 'response_metadata', {}).get('finish_reason') or 'unknown'
            except Exception:
                fr = 'unknown'
            print(f"[LLM] 空响应 attempt={attempt+1}/{max_attempts} finish_reason={fr}", flush=True)
            last_err = f"LLM 返回空内容（finish_reason={fr}）"
        except Exception as e:
            print(f"[LLM] 异常 attempt={attempt+1}/{max_attempts} {type(e).__name__}: {e}", flush=True)
            last_err = str(e)
        if attempt < max_attempts - 1:
            # 指数退避：1.5s → 3s → 4.5s → 6s
            _t.sleep(sleep_s * (attempt + 1))
    return None, last_err or "LLM 重试耗尽"


def _extract_json(text: str):
    """健壮提取 JSON"""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ============================================================
# 工具1: JD 分析器
# ============================================================

class JDAnalyzerInput(BaseModel):
    jd: str = Field(description="完整的职位描述(JD)文本")


class JDAnalyzerTool(BaseTool):
    name: str = "analyze_jd"
    description: str = (
        "分析职位描述(JD)，返回结构化 JSON（position_title / hard_skills / "
        "experience_years / responsibilities 等 25+ 字段）。输入参数 jd 为JD 全文。"
    )
    args_schema: Type[BaseModel] = JDAnalyzerInput

    def _run(self, jd: str) -> str:
        if not (jd and jd.strip()):
            return "[错误] JD 内容为空，无法分析"
        api_key = _api_key()
        llm = _get_llm(api_key, _base_url(), _model(), temperature=0.1, max_tokens=2000)
        # 重试 3 次：防止偶发 LLM 返空
        content, err = _invoke_with_retry(llm, [
            SystemMessage(content=JD_ANALYZER_SYSTEM),
            HumanMessage(content=JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd)),
        ])
        if not content:
            return f"[错误] JD 分析失败：{err}"
        parsed = _extract_json(content)
        if parsed:
            return json.dumps(parsed, ensure_ascii=False)
        # JSON 解析失败也保留原始内容（前端 _try_parse_json 会再尝试一次）
        return content


# ============================================================
# 工具2: 简历匹配器
# ============================================================

class ResumeMatchInput(BaseModel):
    jd_analysis: str = Field(description="analyze_jd 工具返回的完整 JSON 字符串（必填）")
    resume: str = Field(description="候选人简历全文（必填）")


class ResumeMatchTool(BaseTool):
    name: str = "match_resume"
    description: str = (
        "按 A-H 8 段式框架评估简历与目标职位的匹配程度。必填参数："
        "jd_analysis = 上一步 analyze_jd 返回的完整 JSON 字符串；"
        "resume = 候选人简历全文。"
        "返回 JSON（A-H 8 段 + 向后兼容字段）：\n"
        "  A. role_summary：1-2 句角色摘要\n"
        "  B. requirements：5-10 条要求逐项匹配（importance / weight_source=jd_explicit|jd_structure|estimated / resume_match / evidence）\n"
        "  C. level_strategy：资历差距 + 调整建议\n"
        "  D. compensation：JD 薪资 / 市场参考 / fit 评估\n"
        "  E. personalization：2-4 条个性化切入点\n"
        "  F. interview_prep：3-5 个面试题 + 回答方向\n"
        "  G. legitimacy：可信度 + 0-3 条结构化红旗（防骗/防僵尸 JD）\n"
        "  H. form_answers：≥4.5 分才生成的应用表单答案（v2 支持）\n"
        "  + match_score (0-100) / score_breakdown / matched_points / gap_points / overall_assessment（向后兼容）"
    )
    args_schema: Type[BaseModel] = ResumeMatchInput

    def _run(self, jd_analysis: str, resume: str) -> str:
        if not (resume and resume.strip()):
            return "[错误] 简历内容为空，无法匹配"
        api_key = _api_key()
        vector_store = get_vector_store()
        vector_store.add_resume(resume, metadata={"type": "resume"})
        rag_context = vector_store.search_all(resume, top_k=3)

        resume_for_llm = resume[:2500] if len(resume) > 2500 else resume

        llm = _get_llm(api_key, _base_url(), _model(), temperature=0.3, max_tokens=2000)
        # 重试 3 次：防止偶发 LLM 返空
        content, err = _invoke_with_retry(llm, [
            SystemMessage(content=RESUME_MATCH_SYSTEM),
            HumanMessage(content=RESUME_MATCH_USER_TEMPLATE.format(
                jd_analysis=jd_analysis,
                resume_text=resume_for_llm,
                rag_context=rag_context,
            )),
        ])
        if not content:
            return f"[错误] 简历匹配失败：{err}"
        parsed = _extract_json(content)
        if parsed:
            return json.dumps(parsed, ensure_ascii=False)
        return content


# ============================================================
# 工具3: 简历改写器
# ============================================================

class ResumeTailorInput(BaseModel):
    jd: str = Field(description="match_resume 工具返回的 match_result（必填，含分数与诊断）")
    match_result: str = Field(description="同上（兼容性）")
    resume: str = Field(description="原始简历全文（必填）")


class ResumeTailorTool(BaseTool):
    name: str = "tailor_resume"
    description: str = (
        "根据 match_resume 返回的匹配诊断，定向改写简历。"
        "必填：jd = match_resume 的输出；resume = 原始简历。"
        "返回改写后的完整简历（含【改动说明：xxx】标注）。"
    )
    args_schema: Type[BaseModel] = ResumeTailorInput

    def _run(self, jd: str = "", match_result: str = "", resume: str = "") -> str:
        # 兼容 jd / match_result 两种入参
        final_jd = match_result or jd
        resume_truncated = resume[:2500] if len(resume) > 250 else resume
        if not resume_truncated:
            return "[错误] 简历内容为空，无法改写"

        api_key = _api_key()
        llm = _get_llm(api_key, _base_url(), _model(), temperature=0.6, max_tokens=4500)
        # 重试 3 次：防止偶发 LLM 返空
        content, err = _invoke_with_retry(llm, [
            SystemMessage(content=RESUME_TAILOR_SYSTEM),
            HumanMessage(content=RESUME_TAILOR_USER_TEMPLATE.format(
                jd_analysis=final_jd,
                resume_text=resume_truncated,
            )),
        ])
        if content:
            return content
        return f"[错误] 简历改写失败：{err}"


# ============================================================
# 工具4: 求职信生成器
# ============================================================

class CoverLetterInput(BaseModel):
    jd: str = Field(description="职位描述文本")
    resume: str = Field(description="候选人简历")
    candidate_name: str = Field(description="候选人姓名")
    style: str = Field(default="formal", description="求职信风格：formal/casual/tech")
    recipient: str = Field(default="招聘负责人", description="收信人称谓")


class CoverLetterTool(BaseTool):
    name: str = "generate_cover_letter"
    description: str = (
        "生成个性化求职信。Chain-of-Thought 三步：1)分析公司需求 2)匹配个人经历 "
        "3)生成正文。支持 formal/casual/tech。"
        "输入 jd / resume / candidate_name / style / recipient。"
    )
    args_schema: Type[BaseModel] = CoverLetterInput

    def _run(self, jd: str, resume: str, candidate_name: str,
             style: str = "formal", recipient: str = "招聘负责人") -> str:
        if not (resume and resume.strip()):
            return "[错误] 简历内容为空，无法生成求职信"
        if not (jd and jd.strip()):
            return "[错误] JD 内容为空，无法生成求职信"

        api_key = _api_key()
        llm = _get_llm(api_key, _base_url(), _model(), temperature=0.7, max_tokens=3000)

        # Step 1: 公司分析（重试 3 次）
        company_analysis, err1 = _invoke_with_retry(llm, [
            SystemMessage(content=COMPANY_ANALYSIS_SYSTEM),
            HumanMessage(content=COMPANY_ANALYSIS_TEMPLATE.replace("{jd_text}", jd)),
        ])
        if not company_analysis:
            return f"[错误] 求职信公司分析失败：{err1}"

        vector_store = get_vector_store()
        vector_store.add_resume(resume)
        rag_context = vector_store.search_all(resume, top_k=3)

        # Step 2: 经历匹配（重试 3 次）
        exp_tpl = EXPERIENCE_MATCH_TEMPLATE
        exp_tpl = exp_tpl.replace("{company_analysis}", company_analysis)
        exp_tpl = exp_tpl.replace("{resume_text}", resume)
        exp_tpl = exp_tpl.replace("{rag_context}", rag_context)
        exp_tpl = re.sub(r"\{(\w+)\}", r"[\1]", exp_tpl)
        selling_points, err2 = _invoke_with_retry(llm, [
            SystemMessage(content=EXPERIENCE_MATCH_SYSTEM),
            HumanMessage(content=exp_tpl),
        ])
        if not selling_points:
            return f"[错误] 求职信经历匹配失败：{err2}"

        # Step 3: 生成正文（重试 3 次）
        template = COVER_LETTER_TEMPLATE
        template = template.replace("{style}", style)
        template = template.replace("{jd_analysis}", company_analysis)
        template = template.replace("{resume_text}", resume)
        template = template.replace("{core_selling_points}", selling_points)
        template = template.replace("{candidate_name}", candidate_name)
        template = template.replace("{recipient}", recipient)
        template = re.sub(r"\{(\w+)\}", r"[\1]", template)

        final, err3 = _invoke_with_retry(llm, [
            SystemMessage(content=COVER_LETTER_SYSTEM),
            HumanMessage(content=template),
        ])
        if not final:
            return f"[错误] 求职信生成失败：{err3}"
        return final


# ============================================================
# 全局配置 hook（避免循环 import）
# ============================================================

def _api_key() -> str:
    import config
    return config.DEEPSEEK_API_KEY


def _base_url() -> str:
    import config
    return config.DEEPSEEK_BASE_URL


def _model() -> str:
    import config
    return config.DEEPSEEK_MODEL


def get_all_tools() -> list:
    """获取所有 Agent 工具"""
    return [
        JDAnalyzerTool(),
        ResumeMatchTool(),
        ResumeTailorTool(),
        CoverLetterTool(),
    ]