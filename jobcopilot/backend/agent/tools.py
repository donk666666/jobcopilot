"""
LangChain ReAct Agent 工具集

定义了JobCopilot的4个核心工具：
1. analyze_jd — JD结构化分析
2. match_resume — 简历匹配度评分
3. tailor_resume — 简历定向改写
4. generate_cover_letter — 求职信生成
"""

import json
import re
from typing import Type, Optional
from langchain_core.tools import BaseTool
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


# ============================================================
# 工具1: JD分析器
# ============================================================

class JDAnalyzerInput(BaseModel):
    jd_text: str = Field(description="完整的职位描述(JD)文本")


class JDAnalyzerTool(BaseTool):
    name: str = "analyze_jd"
    description: str = "分析职位描述(JD)，提取技能要求、经验要求、公司文化等结构化信息。输入为JD全文文本。"
    args_schema: Type[BaseModel] = JDAnalyzerInput

    def _run(self, jd_text: str) -> str:
        """调用LLM分析JD（在Agent工具中返回prompt，由外部LLM执行）"""
        # Agent工具中返回提示给LLM，让LLM自行处理
        system_prompt = JD_ANALYZER_SYSTEM
        user_prompt = JD_ANALYZER_USER_TEMPLATE.format(jd_text=jd_text)
        return f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"


# ============================================================
# 工具2: 简历匹配器
# ============================================================

class ResumeMatchInput(BaseModel):
    jd_analysis: str = Field(description="已分析好的JD结构化信息")
    resume_text: str = Field(description="候选人简历全文")


class ResumeMatchTool(BaseTool):
    name: str = "match_resume"
    description: str = (
        "评估简历与目标职位的匹配程度，给出0-100的匹配分数和优化建议。"
        "输入为JD分析结果和简历全文。会自动进行RAG检索增强。"
    )
    args_schema: Type[BaseModel] = ResumeMatchInput

    def _run(self, jd_analysis: str, resume_text: str) -> str:
        # RAG检索
        vector_store = get_vector_store()
        # 先确保简历已入库
        vector_store.add_resume(resume_text, metadata={"type": "resume"})
        # 检索相关上下文
        rag_context = vector_store.search_all(resume_text, top_k=3)

        system_prompt = RESUME_MATCH_SYSTEM
        user_prompt = RESUME_MATCH_USER_TEMPLATE.format(
            jd_analysis=jd_analysis,
            resume_text=resume_text,
            rag_context=rag_context
        )
        return f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"


# ============================================================
# 工具3: 简历改写器
# ============================================================

class ResumeTailorInput(BaseModel):
    jd_analysis: str = Field(description="目标职位的JD分析结果")
    match_result: str = Field(description="匹配度分析结果")
    resume_text: str = Field(description="原始简历全文")


class ResumeTailorTool(BaseTool):
    name: str = "tailor_resume"
    description: str = (
        "根据JD要求和匹配度分析结果，定向优化简历表述。"
        "保持真实不虚构，仅优化措辞和结构。"
    )
    args_schema: Type[BaseModel] = ResumeTailorInput

    def _run(self, jd_analysis: str, match_result: str, resume_text: str) -> str:
        system_prompt = RESUME_TAILOR_SYSTEM
        user_prompt = RESUME_TAILOR_USER_TEMPLATE.format(
            jd_analysis=jd_analysis,
            match_result=match_result,
            resume_text=resume_text
        )
        return f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"


# ============================================================
# 工具4: 求职信生成器
# ============================================================

class CoverLetterInput(BaseModel):
    jd_text: str = Field(description="职位描述文本")
    resume_text: str = Field(description="候选人简历")
    candidate_name: str = Field(description="候选人姓名")
    style: str = Field(default="formal", description="求职信风格：formal/casual/tech")
    recipient: str = Field(default="招聘负责人", description="收信人称谓")


class CoverLetterTool(BaseTool):
    name: str = "generate_cover_letter"
    description: str = (
        "生成个性化求职信。支持三种风格：formal(正式商务)、casual(亲和自然)、tech(技术极客)。"
        "使用Chain-of-Thought链式Prompt技术。"
    )
    args_schema: Type[BaseModel] = CoverLetterInput

    def _run(
        self,
        jd_text: str,
        resume_text: str,
        candidate_name: str,
        style: str = "formal",
        recipient: str = "招聘负责人"
    ) -> str:
        # Chain 1: 公司需求分析
        chain1 = COMPANY_ANALYSIS_TEMPLATE.format(jd_text=jd_text)

        # Chain 2: 个人经历匹配（含RAG）
        vector_store = get_vector_store()
        vector_store.add_resume(resume_text)
        rag_context = vector_store.search_all(resume_text, top_k=3)

        # Chain 3: 求职信生成
        chain3 = COVER_LETTER_TEMPLATE.format(
            style=style,
            jd_analysis="{公司需求分析结果}",
            core_selling_points="{核心卖点分析结果}",
            candidate_name=candidate_name,
            recipient=recipient
        )

        # 将所有链组合成一个完整prompt
        full_prompt = f"""请按以下三个步骤依次完成求职信生成。

## 步骤1：公司需求分析
SYSTEM: {COMPANY_ANALYSIS_SYSTEM}
USER: {chain1}

## 步骤2：个人经历匹配
SYSTEM: {EXPERIENCE_MATCH_SYSTEM}
USER: {EXPERIENCE_MATCH_TEMPLATE.format(
    company_analysis="【步骤1的结果】",
    resume_text=resume_text,
    rag_context=rag_context
)}

## 步骤3：生成求职信
SYSTEM: {COVER_LETTER_SYSTEM}
USER: {chain3}

请依次完成以上三个步骤，最终在步骤3中输出完整的求职信。"""

        return f"SYSTEM: 请按Chain-of-Thought方式依次完成任务。\n\nUSER: {full_prompt}"


# ============================================================
# 工具注册
# ============================================================

def get_all_tools() -> list:
    """获取所有Agent工具"""
    return [
        JDAnalyzerTool(),
        ResumeMatchTool(),
        ResumeTailorTool(),
        CoverLetterTool()
    ]
