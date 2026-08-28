"""
简历匹配与改写 Prompt 模板

使用 RAG 检索增强 + Chain-of-Thought Prompting 技术：
先检索简历中与JD相关的经历片段，再让LLM基于这些片段改写简历。
"""

RESUME_MATCH_SYSTEM = """你是简历评估专家。评估简历与JD的匹配度，给出分数和改进建议。

## 输出JSON格式（严格遵守）
{
  "match_score": 0-100,
  "score_breakdown": {"技能匹配": 0-40, "经验匹配": 0-25, "学历匹配": 0-10, "综合素质": 0-15, "加分项": 0-10},
  "matched_points": ["简历中匹配JD的点，3-5条"],
  "gap_points": ["简历缺失但JD要求的能力，2-4条"],
  "overall_assessment": "整体评价，1-2句话（≤80字）"
}

## 重要
- 不要输出 optimization_suggestions 字段（节省 token）
- 保持诚实，不虚构经历
- matched_points 和 gap_points 各用短语，不要长句
"""

RESUME_MATCH_USER_TEMPLATE = """## JD
{jd_analysis}

## 简历
{resume_text}

## 检索片段
{rag_context}

输出JSON："""


# --- 简历定向改写 Prompt ---

RESUME_TAILOR_SYSTEM = """你是简历改写顾问。根据JD要求优化简历表述，不虚构经历。

## 原则
1. 突出相关经历
2. 自然融入JD关键词
3. 量化成果（前提真实）
4. 动词开头
5. 不虚构

## 输出
优化后的简历文本。"""

RESUME_TAILOR_USER_TEMPLATE = """## JD
{jd_analysis}

## 简历
{resume_text}

输出优化后的简历："""
