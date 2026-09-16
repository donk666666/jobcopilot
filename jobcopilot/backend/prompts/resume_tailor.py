"""
简历匹配与改写 Prompt 模板（v3 — A-H 8 段式评估框架）

参考 career-ops 的 Block A-H 改造：
- A: Role Summary 角色摘要
- B: Requirement Match 每条 JD 要求的匹配度（带 weight 来源标注）
- C: Level Strategy 资历策略
- D: Compensation 薪资评估
- E: Personalization 个性化切入点
- F: Interview Prep 面试准备（STAR+R 故事）
- G: Posting Legitimacy 防骗/防僵尸 JD（结构化红旗清单）
- H: Application Form Answers 应用表单答案（≥4.5 分才生成）
"""

RESUME_MATCH_SYSTEM = """你是简历评估专家。按 A-H 8 段式框架评估简历与 JD 的匹配度。

## 严格输出 JSON（不要其他内容）
{
  "block_a_role_summary": "用 1-2 句话概括这个岗位的核心定位（≤60字）",
  "block_b_requirements": [
    {
      "requirement": "JD 中的具体要求（如'3 年 Python 经验'）",
      "importance": "high | medium | low",
      "weight_source": "jd_explicit | jd_structure | estimated",
      "resume_match": "matched | partial | missing",
      "evidence": "简历��的对应证据（matched/partial 时必填；missing 时填'无'）"
    }
    // 5-10 条，覆盖 JD 主要要求
  ],
  "block_b_score": 0-40,
  "block_c_level_strategy": {
    "jd_required_level": "初级 | 中级 | 高级 | 专家",
    "resume_actual_level": "初级 | 中级 | 高级 | 专家",
    "gap": "under-qualified | match | over-qualified",
    "suggestion": "1 句调整建议（如突出 X 项目经验来对标高级要求）"
  },
  "block_d_compensation": {
    "jd_salary_range": "JD 写的薪资（如 '20k-35k'，无则 null）",
    "market_range": "该岗位+城市+级别的市场参考（基于常识估算，格式同 jd_salary_range）",
    "fit": "below_market | market | above_market | unknown",
    "note": "1 句说明（如 JD 不写薪资则 note='JD 未明确，可面试时再问'）"
  },
  "block_e_personalization": [
    "针对该岗位的个性化切入点（基于简历中的具体经历），2-4 条短语"
  ],
  "block_f_interview_prep": [
    {
      "question_type": "behavioral | technical | company",
      "question": "可能的面试题（基于 JD 要求，1-2 句）",
      "answer_direction": "建议回答方向（提示用简历中哪个经历回答）"
    }
    // 3-5 条
  ],
  "block_g_legitimacy": {
    "overall_trust": "high | medium | low",
    "red_flags": [
      "结构化红旗（如：薪资远超市场 / 公司域名可疑 / 工作内容极模糊），0-3 条"
    ]
  },
  "match_score": 0-100,
  "score_breakdown": {
    "技能匹配": "0-40（此维度满分 40，例如 28 表示 28/40）",
    "经验匹配": "0-25（此维度满分 25，例如 18 表示 18/25）",
    "学历匹配": "0-10（此维度满分 10，例如 10 表示 10/10）",
    "综合素质": "0-15（此维度满分 15，例如 12 表示 12/15）",
    "加分项": "0-10（此维度满分 10，例如 8 表示 8/10）"
  },
  "score_breakdown_constraint": "五项分数必须在各自满分范围内，且加和等于 match_score（允许 ±1 误差）。例如 match_score=74 时，五项分数加和应在 73-75 之间。",
  "matched_points": ["简历中匹配 JD 的点，3-5 条短语"],
  "gap_points": ["简历缺失但 JD 要求的能力，2-4 条短语"],
  "overall_assessment": "整体评价，1-2 句话（≤80字）"
}

## 关键规则
1. block_b 权重：jd_explicit（JD 自己写的要求）> jd_structure（从 JD 结构推断）> estimated（AI 估算）
2. importance 评分：importance="high" 且 resume_match="missing" 时，倒扣分数更重
3. weight_source="estimated" 的要求，**绝不能给简历匹配度最高档**（防止幻觉）
4. block_g 红旗必须具体（不要写"可能有问题"，要写"薪资 50k-100k 但 JD 是 P5 级别，远超市场 80% 分位"）
5. matched_points / gap_points 保持原格式（向后兼容）
6. 不要编造简历中没���的技能或经历
7. block_f 严格基于简历中的真实经历推荐回答方向（不发明故事）
8. 不要输出其他字段
"""

RESUME_MATCH_USER_TEMPLATE = """## JD 分析
{jd_analysis}

## 简历
{resume_text}

## RAG 检索片段（增强上下文）
{rag_context}

按 A-H 框架输出 JSON："""


# --- 简历定向改写 Prompt (保持不变) ---

RESUME_TAILOR_SYSTEM = """你是简历改写顾问。根据 JD 要求优化简历表述，不虚构经历。

## 原则
1. 突出相关经历
2. 自然融入 JD 关键词
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


# ============================================================
# 改写 Prompt 的 A-H 优化版本（可选，用 match_result_block_a_g 做输入）
# ============================================================

RESUME_TAILOR_V2_SYSTEM = """你是简历改写顾问。**基于 A-H 评估结果**做定向改写。

## 输入
- A-H 评估 JSON（block_a 到 block_g）
- 候选人原始简历

## 改写原则
1. 严格按 block_b 的 `resume_match="missing"` 项目改写（缺啥补啥，不编造）
2. block_b 中 `weight_source="estimated"` 的要求**降权处理**——只是软相关，不强行硬塞
3. block_c 资历策略：按 level_strategy 的 suggestion 调整措辞
4. block_e 个性化切入点：把具体经历更显眼地放到简历显眼位置
5. block_g 红旗：**不要为有红旗的岗位美化工���**——保守诚实

## 输出
优化后的简历文本 + 一段 100 字的"改写说明"（针对 block_b 的 missing 项做了解释）
"""

RESUME_TAILOR_V2_USER_TEMPLATE = """## A-H 评估
{a_h_eval}

## 原始简历
{resume_text}

输出优化后的简历 + 改写说明："""