"""
多智能体协作系统 — 基于 LangGraph StateGraph

架构：
  Supervisor（路由器）→ 根据用户意图分发到子 Agent
    ├── JD Analyzer → 并行多维度分析 → 辩论汇总 → Resume Matcher → Resume Tailor → Cover Letter
    └── (简化路径) JD Analyzer → Resume Matcher → Resume Tailor → Cover Letter

支持三种流水线模式：
  - jd_analysis:   JD Analyzer → END
  - full_pipeline: JD Analyzer → Parallel Analysis → Debate Summary → Resume Matcher → Resume Tailor → Cover Letter → END
  - cover_letter:  Cover Letter → END
"""

import asyncio
import json
import time
from typing import TypedDict, Literal, Optional, Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


# ============================================================
# LLM 工厂
# ============================================================

def _create_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=DEEPSEEK_MODEL,
        temperature=temperature,
    )


# ============================================================
# 状态定义
# ============================================================

class MultiAgentState(TypedDict):
    user_question: str
    intent: str                      # jd_analysis / full_pipeline / cover_letter
    jd_text: str
    resume_text: str
    candidate_name: str
    style: str                       # formal / casual / tech
    recipient: str

    # 中间结果
    jd_analysis: Optional[str]
    match_result: Optional[str]
    tailored_resume: Optional[str]
    cover_letter: Optional[str]

    # 多维度并行分析
    parallel_analyses: Optional[Dict[str, Any]]     # {tech_stack: {...}, project_exp: {...}, ...}
    dimension_scores: Optional[Dict[str, int]]       # {tech_stack: 75, project_exp: 70, ...}
    contradictions: Optional[List[str]]               # ["技术栈(75) vs 项目经验(40) 存在较大分歧"]

    # 元信息
    stage_timings: Dict[str, float]
    errors: List[str]
    final_output: Optional[str]


# ============================================================
# Supervisor 路由器
# ============================================================

SUPERVISOR_PROMPT = """你是一个多智能体系统的路由器。根据用户的问题，判断应该走哪条流水线。

可选路线：
- jd_analysis: 用户只想分析JD（职位描述）
- full_pipeline: 用户想完整走一遍：分析JD → 匹配简历 → 改写简历 → 生成求职信
- cover_letter: 用户只想要生成求职信

请只回复 JSON：{"intent": "<路线>", "reason": "<简短原因>"}"""


def supervisor_node(state: MultiAgentState) -> dict:
    """Supervisor 路由节点：分析用户意图，决定流水线"""
    llm = _create_llm(temperature=0.0)

    resp = llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=state["user_question"]),
    ])

    try:
        result = json.loads(resp.content)
        intent = result.get("intent", "full_pipeline")
    except json.JSONDecodeError:
        intent = "full_pipeline"

    valid = {"jd_analysis", "full_pipeline", "cover_letter"}
    if intent not in valid:
        intent = "full_pipeline"

    return {"intent": intent}


def route_by_intent(state: MultiAgentState) -> Literal["jd_analyzer", "cover_letter", "full_pipeline_start"]:
    """根据 intent 路由到不同起点"""
    intent = state.get("intent", "full_pipeline")
    if intent == "jd_analysis":
        return "jd_analyzer"
    elif intent == "cover_letter":
        return "cover_letter"
    else:
        return "jd_analyzer"  # full_pipeline 从 JD 分析开始


# ============================================================
# 子 Agent 节点
# ============================================================

async def jd_analyzer_node(state: MultiAgentState) -> dict:
    """JD 分析节点"""
    from agent.core import analyze_jd_direct

    t0 = time.time()
    try:
        result = await analyze_jd_direct(
            state["jd_text"], DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        )
        jd_json = json.dumps(result.get("result", {}), ensure_ascii=False) if result.get("result") else str(result.get("raw", ""))
        return {
            "jd_analysis": jd_json,
            "stage_timings": {**state.get("stage_timings", {}), "jd_analyzer": round(time.time() - t0, 2)},
        }
    except Exception as e:
        return {
            "errors": [*state.get("errors", []), f"JD分析失败: {str(e)}"],
            "stage_timings": {**state.get("stage_timings", {}), "jd_analyzer": round(time.time() - t0, 2)},
        }


async def _run_single_agent(dimension_key: str, system_prompt: str, state: MultiAgentState) -> dict:
    """执行单个维度的分析，带 30s 超时保护"""
    llm = _create_llm(temperature=0.3)

    jd_text = state.get("jd_analysis") or state["jd_text"]
    user_prompt = f"""## 职位描述（JD）
{jd_text}

## 求职者简历
{state["resume_text"]}

请根据你的分析维度，对以上简历与JD进行评估，严格按JSON格式输出结果。"""

    try:
        response = await asyncio.wait_for(
            llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]),
            timeout=30,
        )
        content = response.content.strip()
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except asyncio.TimeoutError:
        return {"dimension": dimension_key, "score": 0, "matched": [], "gaps": [], "analysis": "分析超时（30s）", "error": True}
    except Exception as e:
        return {"dimension": dimension_key, "score": 0, "matched": [], "gaps": [], "analysis": f"分析异常: {str(e)}", "error": True}


async def parallel_analysis_node(state: MultiAgentState) -> dict:
    """并行多维度分析节点：4 个 Agent 同时从不同维度评估"""
    from prompts.parallel_agents import AGENT_PROMPTS

    if not state.get("resume_text"):
        return {"errors": [*state.get("errors", []), "并行分析: 缺少简历文本"]}

    t0 = time.time()
    tasks = []
    for dim_key, sys_prompt in AGENT_PROMPTS.items():
        tasks.append(_run_single_agent(dim_key, sys_prompt, state))

    results = await asyncio.gather(*tasks)

    # 整理结果
    parallel_analyses: Dict[str, Any] = {}
    dimension_scores: Dict[str, int] = {}
    errors = list(state.get("errors", []))

    for r in results:
        if r is None:
            continue
        dim = r.get("dimension", "unknown")
        parallel_analyses[dim] = r
        dimension_scores[dim] = r.get("score", 0)
        if r.get("error"):
            errors.append(f"维度 [{dim}] 分析失败（已降级）")

    # 检查是否全部失败
    if not parallel_analyses:
        errors.append("并行分析: 所有维度 Agent 均失败，将降级为单次匹配")
        return {
            "errors": errors,
            "parallel_analyses": {},
            "dimension_scores": {},
            "stage_timings": {**state.get("stage_timings", {}), "parallel_analysis": round(time.time() - t0, 2)},
        }

    return {
        "parallel_analyses": parallel_analyses,
        "dimension_scores": dimension_scores,
        "errors": errors,
        "stage_timings": {**state.get("stage_timings", {}), "parallel_analysis": round(time.time() - t0, 2)},
    }


async def debate_summary_node(state: MultiAgentState) -> dict:
    """辩论汇总节点：综合 4 维度分析，标记矛盾点，输出统一评估"""
    t0 = time.time()
    parallel = state.get("parallel_analyses") or {}

    if not parallel:
        # 降级：所有 Agent 都失败了，跳过汇总
        return {
            "match_result": json.dumps({"error": "多维度分析全部失败，无法汇总"}, ensure_ascii=False),
            "stage_timings": {**state.get("stage_timings", {}), "debate_summary": round(time.time() - t0, 2)},
        }

    # 检测矛盾点：两两比较分差 > 20
    scores = state.get("dimension_scores") or {}
    dims = list(scores.keys())
    contradictions = []
    for i in range(len(dims)):
        for j in range(i + 1, len(dims)):
            diff = abs(scores[dims[i]] - scores[dims[j]])
            if diff > 20:
                contradictions.append(f"{dims[i]}({scores[dims[i]]}) vs {dims[j]}({scores[dims[j]]}) 存在较大分歧(差{diff}分)")

    # 综合评分：加权平均（软技能权重略低）
    weights = {"tech_stack": 0.30, "project_exp": 0.30, "soft_skills": 0.15, "growth": 0.25}
    total_weighted = 0
    total_weight = 0
    for dim, s in scores.items():
        w = weights.get(dim, 0.25)
        total_weighted += s * w
        total_weight += w
    overall_score = round(total_weighted / total_weight) if total_weight > 0 else 0

    # 构建汇总
    summary_parts = [f"综合评分: {overall_score}/100"]
    if contradictions:
        summary_parts.append(f"\n矛盾点: {'; '.join(contradictions)}")

    for dim, data in parallel.items():
        label = {"tech_stack": "技术栈", "project_exp": "项目经验", "soft_skills": "软技能", "growth": "成长潜力"}.get(dim, dim)
        summary_parts.append(f"\n\n【{label}】(评分: {data.get('score', 'N/A')}/100)")
        summary_parts.append(data.get("analysis", ""))

    # 生成统一的 matched/gaps
    all_matched = []
    all_gaps = []
    for data in parallel.values():
        all_matched.extend(data.get("matched", []))
        all_gaps.extend(data.get("gaps", []))

    match_result = {
        "overall_score": overall_score,
        "dimension_scores": scores,
        "contradictions": contradictions,
        "matched_points": all_matched,
        "gap_points": all_gaps,
        "summary": "\n".join(summary_parts),
    }

    return {
        "match_result": json.dumps(match_result, ensure_ascii=False),
        "contradictions": contradictions,
        "stage_timings": {**state.get("stage_timings", {}), "debate_summary": round(time.time() - t0, 2)},
    }


async def resume_matcher_node(state: MultiAgentState) -> dict:
    """简历匹配节点 — 仅在跳过并行分析时使用"""
    from agent.core import match_resume_direct

    if not state.get("jd_analysis"):
        return {"errors": [*state.get("errors", []), "简历匹配: 缺少JD分析结果"]}

    # 如果已有并行分析结果（debate_summary已生成），跳过
    if state.get("match_result"):
        return {}

    t0 = time.time()
    try:
        result = await match_resume_direct(
            state["jd_analysis"], state["resume_text"], DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        )
        match_json = json.dumps(result.get("result", {}), ensure_ascii=False) if result.get("result") else str(result.get("raw", ""))
        return {
            "match_result": match_json,
            "stage_timings": {**state.get("stage_timings", {}), "resume_matcher": round(time.time() - t0, 2)},
        }
    except Exception as e:
        return {
            "errors": [*state.get("errors", []), f"简历匹配失败: {str(e)}"],
            "stage_timings": {**state.get("stage_timings", {}), "resume_matcher": round(time.time() - t0, 2)},
        }


async def resume_tailor_node(state: MultiAgentState) -> dict:
    """简历改写节点"""
    from agent.core import tailor_resume_direct

    if not state.get("jd_analysis") or not state.get("match_result"):
        return {"errors": [*state.get("errors", []), "简历改写: 缺少前置结果"]}

    t0 = time.time()
    try:
        result = await tailor_resume_direct(
            state["jd_analysis"], state["match_result"], state["resume_text"],
            DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
        )
        return {
            "tailored_resume": result.get("result", ""),
            "stage_timings": {**state.get("stage_timings", {}), "resume_tailor": round(time.time() - t0, 2)},
        }
    except Exception as e:
        return {
            "errors": [*state.get("errors", []), f"简历改写失败: {str(e)}"],
            "stage_timings": {**state.get("stage_timings", {}), "resume_tailor": round(time.time() - t0, 2)},
        }


async def cover_letter_node(state: MultiAgentState) -> dict:
    """求职信生成节点"""
    from agent.core import generate_cover_letter_direct

    t0 = time.time()
    jd_text = state.get("jd_analysis") or state["jd_text"]
    try:
        result = await generate_cover_letter_direct(
            jd_text=jd_text,
            resume_text=state.get("tailored_resume") or state["resume_text"],
            candidate_name=state.get("candidate_name", "求职者"),
            style=state.get("style", "formal"),
            recipient=state.get("recipient", "招聘负责人"),
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        return {
            "cover_letter": result.get("result", ""),
            "stage_timings": {**state.get("stage_timings", {}), "cover_letter": round(time.time() - t0, 2)},
        }
    except Exception as e:
        return {
            "errors": [*state.get("errors", []), f"求职信生成失败: {str(e)}"],
            "stage_timings": {**state.get("stage_timings", {}), "cover_letter": round(time.time() - t0, 2)},
        }


async def finalize_node(state: MultiAgentState) -> dict:
    """汇总结果"""
    output_parts = []
    intent = state.get("intent", "full_pipeline")

    if state.get("jd_analysis"):
        output_parts.append(f"## JD 分析结果\n{state['jd_analysis']}")

    if intent == "full_pipeline" and state.get("match_result"):
        output_parts.append(f"## 简历匹配结果\n{state['match_result']}")

    # 多维度分析摘要
    dim_scores = state.get("dimension_scores") or {}
    if dim_scores:
        score_lines = []
        labels = {"tech_stack": "技术栈", "project_exp": "项目经验", "soft_skills": "软技能", "growth": "成长潜力"}
        for dim, s in dim_scores.items():
            label = labels.get(dim, dim)
            bar = "█" * (s // 10) + "░" * (10 - s // 10)
            score_lines.append(f"- {label}: {bar} {s}/100")
        output_parts.append("## 多维度评分\n" + "\n".join(score_lines))

    contradictions = state.get("contradictions") or []
    if contradictions:
        output_parts.append("## 分析矛盾点\n" + "\n".join(f"- {c}" for c in contradictions))

    if intent == "full_pipeline" and state.get("tailored_resume"):
        output_parts.append(f"## 改写后简历\n{state['tailored_resume']}")

    if state.get("cover_letter"):
        output_parts.append(f"## 求职信\n{state['cover_letter']}")

    if state.get("errors"):
        output_parts.append(f"## 错误\n" + "\n".join(f"- {e}" for e in state["errors"]))

    # 性能摘要
    timings = state.get("stage_timings", {})
    if timings:
        total = sum(timings.values())
        perf = f"\n\n---\n**流水线耗时**: {total:.1f}s ({', '.join(f'{k}: {v}s' for k, v in timings.items())})"
        output_parts.append(perf)

    return {"final_output": "\n\n".join(output_parts)}


# ============================================================
# 路由函数
# ============================================================

def after_jd_analyzer(state: MultiAgentState) -> Literal["parallel_analysis", "resume_matcher", "cover_letter", "finalize"]:
    """JD 分析完成后：full_pipeline(有简历) → 并行分析, jd_analysis → 汇总"""
    if state.get("intent") == "jd_analysis":
        return "finalize"
    if state.get("resume_text"):
        return "parallel_analysis"
    return "resume_matcher"


def after_parallel(state: MultiAgentState) -> Literal["debate_summary", "resume_matcher"]:
    """并行分析完成 → 辩论汇总"""
    if state.get("parallel_analyses"):
        return "debate_summary"
    return "resume_matcher"  # 降级：全部失败则走老路径


def after_debate(state: MultiAgentState) -> Literal["resume_tailor", "finalize"]:
    if state.get("errors"):
        # 检查是否有致命错误（无 match_result）
        if not state.get("match_result"):
            return "finalize"
    return "resume_tailor"


def after_matcher(state: MultiAgentState) -> Literal["resume_tailor", "finalize"]:
    if state.get("errors") and not state.get("match_result"):
        return "finalize"
    return "resume_tailor"


def after_tailor(state: MultiAgentState) -> Literal["cover_letter", "finalize"]:
    if state.get("errors") and not state.get("tailored_resume"):
        return "finalize"
    return "cover_letter"


# ============================================================
# 构建图
# ============================================================

def build_multi_agent_graph() -> StateGraph:
    """构建多智能体 LangGraph 流水线"""
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("jd_analyzer", jd_analyzer_node)
    workflow.add_node("parallel_analysis", parallel_analysis_node)
    workflow.add_node("debate_summary", debate_summary_node)
    workflow.add_node("resume_matcher", resume_matcher_node)
    workflow.add_node("resume_tailor", resume_tailor_node)
    workflow.add_node("cover_letter", cover_letter_node)
    workflow.add_node("finalize", finalize_node)

    # 入口 → Supervisor
    workflow.set_entry_point("supervisor")

    # Supervisor → 路由
    workflow.add_conditional_edges("supervisor", route_by_intent, {
        "jd_analyzer": "jd_analyzer",
        "cover_letter": "cover_letter",
    })

    # JD分析后的路由
    workflow.add_conditional_edges("jd_analyzer", after_jd_analyzer, {
        "parallel_analysis": "parallel_analysis",
        "resume_matcher": "resume_matcher",
        "cover_letter": "cover_letter",
        "finalize": "finalize",
    })

    # 并行分析 → 辩论汇总
    workflow.add_conditional_edges("parallel_analysis", after_parallel, {
        "debate_summary": "debate_summary",
        "resume_matcher": "resume_matcher",
    })

    # 辩论汇总 → 简历改写
    workflow.add_conditional_edges("debate_summary", after_debate, {
        "resume_tailor": "resume_tailor",
        "finalize": "finalize",
    })

    # 匹配 → 改写
    workflow.add_conditional_edges("resume_matcher", after_matcher, {
        "resume_tailor": "resume_tailor",
        "finalize": "finalize",
    })

    # 改写 → 求职信
    workflow.add_conditional_edges("resume_tailor", after_tailor, {
        "cover_letter": "cover_letter",
        "finalize": "finalize",
    })

    # 求职信 → 汇总
    workflow.add_edge("cover_letter", "finalize")

    # 汇总 → 结束
    workflow.add_edge("finalize", END)

    return workflow.compile()


# ============================================================
# 便捷调用
# ============================================================

_multi_agent_app = None


def get_multi_agent():
    global _multi_agent_app
    if _multi_agent_app is None:
        _multi_agent_app = build_multi_agent_graph()
    return _multi_agent_app


async def run_multi_agent(
    question: str,
    jd_text: str = "",
    resume_text: str = "",
    candidate_name: str = "求职者",
    style: str = "formal",
    recipient: str = "招聘负责人",
) -> Dict[str, Any]:
    """运行多智能体流水线"""
    app = get_multi_agent()
    t_start = time.time()

    initial_state: MultiAgentState = {
        "user_question": question,
        "intent": "",
        "jd_text": jd_text,
        "resume_text": resume_text,
        "candidate_name": candidate_name,
        "style": style,
        "recipient": recipient,
        "jd_analysis": None,
        "match_result": None,
        "tailored_resume": None,
        "cover_letter": None,
        "parallel_analyses": None,
        "dimension_scores": None,
        "contradictions": None,
        "stage_timings": {},
        "errors": [],
        "final_output": None,
    }

    result = await app.ainvoke(initial_state)
    total_time = round(time.time() - t_start, 2)

    return {
        "success": len(result.get("errors", [])) == 0,
        "intent": result.get("intent", ""),
        "output": result.get("final_output", ""),
        "dimension_scores": result.get("dimension_scores"),
        "contradictions": result.get("contradictions"),
        "stage_timings": result.get("stage_timings", {}),
        "total_time_s": total_time,
        "errors": result.get("errors", []),
    }
